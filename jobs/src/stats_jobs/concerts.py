"""Upcoming UK gigs by each user's top artists, from Ticketmaster's Discovery API.

Like the picture cache, answers are kept in one JSON file shared by every user,
`catalog/concerts.json`, so an artist two people like is only asked about once:

    artist name   → Ticketmaster's id for them (an "attraction"), or None if it has none
    attraction id → their next few UK events, refreshed about once a day

Each hourly run then writes every user a `concerts` stat document from the cache: their top
artists (best of 4 weeks and 12 months) that have dates announced, favourites first.

Ticketmaster allows 5 requests a second and 5,000 a day, so calls are spaced out and each run
makes at most `CALL_BUDGET`; artists left over are looked up on a later run.
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from datetime import date
from typing import Any

import httpx

log = logging.getLogger()
# httpx logs every request URL at INFO, and Ticketmaster's key is in the URL: keep it out of logs.
logging.getLogger("httpx").setLevel(logging.WARNING)

API_URL = "https://app.ticketmaster.com/discovery/v2"
CONCERTS_KEY = "catalog/concerts.json"
SSM_KEY_NAME = "ticketmaster_api_key"
COUNTRY = "GB"
ARTISTS_PER_USER = 50
EVENTS_PER_ARTIST = 3
EVENTS_TTL_S = 20 * 3600
# Artists Ticketmaster doesn't know are checked again monthly, in case they start touring.
UNKNOWN_TTL_S = 30 * 86400
CALL_BUDGET = 400
MIN_GAP_S = 0.25
IMAGE_WIDTH = 640

Fetch = Callable[[str, dict[str, Any]], dict[str, Any]]


class TicketmasterLimited(Exception):
    """Ticketmaster said to slow down; stop asking for this run."""


def ticketmaster_fetch(
    http: httpx.Client,
    api_key: str,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> Fetch:
    """GET a Discovery API path such as `/events.json`, at most 4 requests a second."""
    last = -MIN_GAP_S

    def fetch(path: str, params: dict[str, Any]) -> dict[str, Any]:
        nonlocal last
        wait = last + MIN_GAP_S - clock()
        if wait > 0:
            sleep(wait)
        last = clock()
        # The key goes in the query string: that's how Ticketmaster takes it. Never log URLs.
        response = http.get(f"{API_URL}{path}", params={**params, "apikey": api_key})
        if response.status_code == 429:
            raise TicketmasterLimited(path)
        response.raise_for_status()
        return response.json()

    return fetch


def _name_key(name: str) -> str:
    return " ".join(name.casefold().split())


def _image(images: list[dict[str, Any]]) -> str | None:
    """The 16:9 picture closest to IMAGE_WIDTH wide, else any."""
    if not images:
        return None
    wide = [i for i in images if i.get("ratio") == "16_9"] or images
    return min(wide, key=lambda i: abs(i.get("width", 0) - IMAGE_WIDTH)).get("url")


def event_summary(event: dict[str, Any]) -> dict[str, Any] | None:
    """The parts of a Ticketmaster event the app shows. None for cancelled ones."""
    dates = event.get("dates", {})
    if dates.get("status", {}).get("code") in {"cancelled", "canceled"}:
        return None
    start = dates.get("start", {})
    venue = (event.get("_embedded", {}).get("venues") or [{}])[0]
    return {
        "name": event.get("name"),
        "date": start.get("localDate"),
        "time": start.get("localTime"),
        "venue": venue.get("name"),
        "city": venue.get("city", {}).get("name"),
        "url": event.get("url"),
        "image": _image(event.get("images", [])),
    }


class Concerts:
    def __init__(
        self,
        fetch: Fetch,
        attractions: dict[str, Any] | None = None,
        events: dict[str, Any] | None = None,
        budget: int = CALL_BUDGET,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.fetch = fetch
        self.attractions: dict[str, Any] = attractions or {}
        self.events: dict[str, Any] = events or {}
        self.budget = budget
        self.clock = clock
        self.calls = 0
        self.stopped = False
        self.changed = False

    @classmethod
    def load(cls, s3: Any, bucket: str, fetch: Fetch, budget: int = CALL_BUDGET) -> Concerts:
        try:
            body = json.loads(s3.get_object(Bucket=bucket, Key=CONCERTS_KEY)["Body"].read())
        except s3.exceptions.NoSuchKey:
            body = {}
        return cls(fetch, body.get("attractions"), body.get("events"), budget)

    def save(self, s3: Any, bucket: str) -> None:
        if not self.changed:
            return
        body = json.dumps({"attractions": self.attractions, "events": self.events})
        s3.put_object(
            Bucket=bucket, Key=CONCERTS_KEY, Body=body.encode(), ContentType="application/json"
        )

    def _call(self, path: str, params: dict[str, Any]) -> dict[str, Any] | None:
        """One API call within the budget; None once the run should stop asking."""
        if self.stopped or self.calls >= self.budget:
            return None
        self.calls += 1
        try:
            return self.fetch(path, params)
        except TicketmasterLimited:
            log.warning("Ticketmaster asked to slow down; stopping for this run")
        except httpx.HTTPError:
            log.exception("Ticketmaster call failed; stopping for this run")
        self.stopped = True
        return None

    def attraction_id(self, artist: str) -> str | None:
        """Ticketmaster's id for an artist, matched on the exact name."""
        key = _name_key(artist)
        cached = self.attractions.get(key)
        if cached and (cached["id"] or self.clock() - cached["checked_at"] < UNKNOWN_TTL_S):
            return cached["id"]
        body = self._call(
            "/attractions.json", {"keyword": artist, "classificationName": "music", "size": 10}
        )
        if body is None:
            return cached["id"] if cached else None
        found = body.get("_embedded", {}).get("attractions", [])
        # Only an exact name: "Weston Estate" mustn't match a tribute act or a festival.
        match = next((a["id"] for a in found if _name_key(a.get("name", "")) == key), None)
        self.attractions[key] = {"id": match, "checked_at": self.clock()}
        self.changed = True
        return match

    def upcoming(self, artist: str) -> list[dict[str, Any]]:
        """The artist's next UK events, from the cache when it's under a day old."""
        attraction = self.attraction_id(artist)
        if attraction is None:
            return []
        cached = self.events.get(attraction)
        if cached and self.clock() - cached["fetched_at"] < EVENTS_TTL_S:
            return cached["events"]
        body = self._call(
            "/events.json",
            {
                "attractionId": attraction,
                "countryCode": COUNTRY,
                "sort": "date,asc",
                "size": EVENTS_PER_ARTIST + 2,
            },
        )
        if body is None:
            return cached["events"] if cached else []
        found = body.get("_embedded", {}).get("events", [])
        events = [e for e in map(event_summary, found) if e][:EVENTS_PER_ARTIST]
        self.events[attraction] = {"fetched_at": self.clock(), "events": events}
        self.changed = True
        return events


def favourite_artists(lists: list[list[dict[str, Any]]], limit: int = ARTISTS_PER_USER) -> list:
    """Merge top-artist lists, each artist at their best rank in any of them."""
    best: dict[str, tuple[int, dict[str, Any]]] = {}
    for rows in lists:
        for rank, row in enumerate(rows, 1):
            key = _name_key(row["name"])
            if key not in best or rank < best[key][0]:
                best[key] = (rank, row)
    ranked = sorted(best.values(), key=lambda pair: pair[0])
    return [{**row, "rank": rank} for rank, row in ranked[:limit]]


def concerts_document(
    artists: list[dict[str, Any]], concerts: Concerts, today: date
) -> list[dict[str, Any]]:
    """The user's favourite artists with UK dates announced, favourites first."""
    out = []
    for artist in artists:
        events = [
            e
            for e in concerts.upcoming(artist["name"])
            if e["date"] and e["date"] >= today.isoformat()
        ]
        if events:
            out.append(
                {
                    "artist": artist["name"],
                    "rank": artist["rank"],
                    "image": artist.get("image"),
                    "url": artist.get("url"),
                    "events": events,
                }
            )
    return out
