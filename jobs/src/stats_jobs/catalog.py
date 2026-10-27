"""Pictures and links for the top lists, from Spotify's catalogue, cached in S3.

Spotify only lets this app (in development mode) look tracks and artists up one at a time, and
no longer returns genres. So each track and artist is looked up once, ever, and kept in one
JSON file shared by every user: `catalog/spotify.json` in the data bucket. A run looks up at
most `LOOKUP_BUDGET` new items; anything left over gets its picture on a later run.

Pictures are Spotify's own image URLs (i.scdn.co), not copies: Spotify wants apps to show its
artwork from its servers.

    track id  → album cover, track and album links, the artists' ids
    artist id → artist photo and link (found through the artist's most-played track)
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from typing import Any

import httpx

from stats_ingest.spotify import API_URL, SpotifyConfig, app_token

log = logging.getLogger()

CATALOG_KEY = "catalog/spotify.json"
LOOKUP_BUDGET = 300
# Longer waits than this end the run's lookups rather than stall the stats job.
MAX_RETRY_AFTER_S = 5
IMAGE_SIZE = 300

Fetch = Callable[[str], dict[str, Any] | None]


class RateLimited(Exception):
    pass


def spotify_fetch(http: httpx.Client, config: SpotifyConfig) -> Fetch:
    """GET a catalogue path such as `/tracks/<id>` as the app. None when it doesn't exist."""
    token = app_token(http, config)

    def fetch(path: str) -> dict[str, Any] | None:
        nonlocal token
        for _ in range(3):
            if token.expired(time.time()):
                token = app_token(http, config)
            response = http.get(
                f"{API_URL}{path}", headers={"Authorization": f"Bearer {token.access_token}"}
            )
            if response.status_code == 429:
                wait = float(response.headers.get("Retry-After", "1"))
                if wait > MAX_RETRY_AFTER_S:
                    raise RateLimited(f"Spotify asked to wait {wait:.0f} s")
                time.sleep(wait)
                continue
            if response.status_code in (400, 404):
                return None
            response.raise_for_status()
            return response.json()
        raise RateLimited("still rate limited")

    return fetch


def pick_image(images: list[dict[str, Any]] | None) -> str | None:
    """The smallest picture at least IMAGE_SIZE wide, or the biggest there is."""
    if not images:
        return None
    by_width = sorted(images, key=lambda i: i.get("width") or 0)
    big_enough = [i for i in by_width if (i.get("width") or 0) >= IMAGE_SIZE]
    return (big_enough[0] if big_enough else by_width[-1])["url"]


def _track_entry(track: dict[str, Any]) -> dict[str, Any]:
    album = track.get("album") or {}
    return {
        "url": (track.get("external_urls") or {}).get("spotify"),
        "album_url": (album.get("external_urls") or {}).get("spotify"),
        "image": pick_image(album.get("images")),
        "artists": [{"id": a["id"], "name": a["name"]} for a in track.get("artists", [])],
    }


def _artist_entry(artist: dict[str, Any]) -> dict[str, Any]:
    return {
        "url": (artist.get("external_urls") or {}).get("spotify"),
        "image": pick_image(artist.get("images")),
    }


class Catalog:
    def __init__(
        self,
        fetch: Fetch,
        tracks: dict[str, Any] | None = None,
        artists: dict[str, Any] | None = None,
        budget: int = LOOKUP_BUDGET,
    ) -> None:
        self.fetch = fetch
        # A cached None means Spotify doesn't know the id, so it isn't asked again.
        self.tracks: dict[str, Any] = tracks or {}
        self.artists: dict[str, Any] = artists or {}
        self.budget = budget
        self.lookups = 0
        self.stopped = False

    @classmethod
    def load(cls, s3: Any, bucket: str, fetch: Fetch, budget: int = LOOKUP_BUDGET) -> Catalog:
        try:
            body = json.loads(s3.get_object(Bucket=bucket, Key=CATALOG_KEY)["Body"].read())
        except s3.exceptions.NoSuchKey:
            body = {}
        return cls(fetch, body.get("tracks"), body.get("artists"), budget)

    def save(self, s3: Any, bucket: str) -> None:
        if not self.lookups:
            return
        body = json.dumps({"tracks": self.tracks, "artists": self.artists}, ensure_ascii=False)
        s3.put_object(
            Bucket=bucket, Key=CATALOG_KEY, Body=body.encode(), ContentType="application/json"
        )

    def _lookup(
        self, cache: dict[str, Any], path: str, key: str, entry: Callable[[dict], dict]
    ) -> dict[str, Any] | None:
        if key in cache:
            return cache[key]
        if self.stopped or self.lookups >= self.budget:
            return None
        self.lookups += 1
        try:
            found = self.fetch(f"{path}/{key}")
        except RateLimited as e:
            log.warning("catalog lookups stopped for this run: %s", e)
            self.stopped = True
            return None
        except Exception:
            log.exception("looking up %s/%s failed", path, key)
            return None
        cache[key] = entry(found) if found else None
        return cache[key]

    def track(self, track_id: str) -> dict[str, Any] | None:
        return self._lookup(self.tracks, "/tracks", track_id, _track_entry)

    def artist(self, artist_id: str) -> dict[str, Any] | None:
        return self._lookup(self.artists, "/artists", artist_id, _artist_entry)

    def describe(self, kind: str, row: dict[str, Any]) -> dict[str, Any]:
        """`image` and `url` for one top-list row of `kind` artist, track or album."""
        track_id = row.get("track_id")
        track = self.track(track_id) if track_id else None
        if not track:
            return {}
        if kind == "track":
            return {"image": track["image"], "url": track["url"]}
        if kind == "album":
            return {"image": track["image"], "url": track["album_url"]}
        # The artist named in the row, not a featured one on their most-played track.
        artists = track["artists"]
        match = next((a for a in artists if a["name"] == row.get("name")), None)
        artist = self.artist(match["id"]) if match else None
        return {"image": artist["image"], "url": artist["url"]} if artist else {}


TOP_KINDS = {"top_artists": "artist", "top_tracks": "track", "top_albums": "album"}


def _rolling_first(stat_name: str) -> tuple[bool, str]:
    # Spend the lookup budget on what the app shows most: recent windows before past years.
    return ("year_" in stat_name or "wrapped" in stat_name, stat_name)


def enrich(documents: dict[str, dict[str, Any]], catalog: Catalog) -> int:
    """Add `image` and `url` to every top-list row that the catalogue can describe, in place.
    Returns how many rows got a picture."""
    pictured = 0

    def add(kind: str, rows: list[dict[str, Any]]) -> None:
        nonlocal pictured
        for row in rows:
            details = catalog.describe(kind, row)
            row.update(details)
            pictured += bool(details.get("image"))

    for stat_name in sorted(documents, key=_rolling_first):
        data = documents[stat_name]["data"]
        base = stat_name.split("#")[0]
        if base in TOP_KINDS:
            add(TOP_KINDS[base], data)
        elif base == "wrapped":
            for name, kind in TOP_KINDS.items():
                add(kind, data.get(name) or [])
    return pictured
