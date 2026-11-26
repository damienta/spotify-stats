"""Pictures and links for the top lists, from Spotify's catalogue, cached in S3.

Spotify only lets this app (in development mode) look tracks and artists up one at a time, and
no longer returns genres. So each track and artist is looked up once, ever, and kept in one
JSON file shared by every user: `catalog/spotify.json` in the data bucket. A run looks up at
most `LOOKUP_BUDGET` new items; anything left over gets its picture on a later run. When
Spotify says to back off (it has asked for nearly 24 hours after a busy day), the file
remembers until when, and no run asks again before then.

Pictures are Spotify's own image URLs (i.scdn.co), not copies: Spotify wants apps to show its
artwork from its servers.

    track id  → album cover, track and album links, the artists' ids
    artist id → artist photo and link (found through the artist's most-played track)
    album id  → the album's tracklist in order (for album pages; the id comes from a track's
                album link)
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
LOOKUP_BUDGET = 500
# Longer waits than this end the run's lookups rather than stall the stats job.
MAX_RETRY_AFTER_S = 5
IMAGE_SIZE = 300

Fetch = Callable[[str], dict[str, Any] | None]


class RateLimited(Exception):
    def __init__(self, message: str, wait_s: float = 0) -> None:
        super().__init__(message)
        self.wait_s = wait_s


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
                    raise RateLimited(f"Spotify asked to wait {wait:.0f} s", wait)
                time.sleep(wait)
                continue
            if response.status_code in (400, 404):
                return None
            response.raise_for_status()
            return response.json()
        raise RateLimited("still rate limited", MAX_RETRY_AFTER_S)

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


def _tracklist_entry(body: dict[str, Any]) -> list[dict[str, Any]]:
    # One page of up to 50 tracks covers all but the longest box sets.
    return [
        {
            "number": t.get("track_number"),
            "disc": t.get("disc_number") or 1,
            "name": t["name"],
            "id": t.get("id"),
        }
        for t in body.get("items", [])
    ]


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
        paused_until: float = 0,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.fetch = fetch
        self.clock = clock
        # Unix time before which Spotify asked not to be asked again.
        self.paused_until = paused_until
        self.changed = False
        # A cached None means Spotify doesn't know the id, so it isn't asked again.
        self.tracks: dict[str, Any] = tracks or {}
        self.artists: dict[str, Any] = artists or {}
        self.albums: dict[str, Any] = {}
        self.budget = budget
        self.lookups = 0
        self.stopped = False

    @classmethod
    def load(cls, s3: Any, bucket: str, fetch: Fetch, budget: int = LOOKUP_BUDGET) -> Catalog:
        try:
            body = json.loads(s3.get_object(Bucket=bucket, Key=CATALOG_KEY)["Body"].read())
        except s3.exceptions.NoSuchKey:
            body = {}
        catalog = cls(
            fetch, body.get("tracks"), body.get("artists"), budget, body.get("paused_until", 0)
        )
        catalog.albums = body.get("albums") or {}
        return catalog

    @property
    def paused(self) -> bool:
        return self.clock() < self.paused_until

    def save(self, s3: Any, bucket: str) -> None:
        if not self.changed:
            return
        body = json.dumps(
            {
                "tracks": self.tracks,
                "artists": self.artists,
                "albums": self.albums,
                "paused_until": self.paused_until,
            },
            ensure_ascii=False,
        )
        s3.put_object(
            Bucket=bucket, Key=CATALOG_KEY, Body=body.encode(), ContentType="application/json"
        )

    def _lookup(
        self,
        cache: dict[str, Any],
        path: str,
        key: str,
        entry: Callable[[dict], Any],
        suffix: str = "",
    ) -> Any:
        if key in cache:
            return cache[key]
        if self.stopped or self.paused or self.lookups >= self.budget:
            return None
        self.lookups += 1
        try:
            found = self.fetch(f"{path}/{key}{suffix}")
        except RateLimited as e:
            log.warning("catalog lookups paused: %s", e)
            self.stopped = True
            self.paused_until = self.clock() + e.wait_s
            self.changed = True
            return None
        except Exception:
            log.exception("looking up %s/%s failed", path, key)
            return None
        cache[key] = entry(found) if found else None
        self.changed = True
        return cache[key]

    def track(self, track_id: str) -> dict[str, Any] | None:
        return self._lookup(self.tracks, "/tracks", track_id, _track_entry)

    def artist(self, artist_id: str) -> dict[str, Any] | None:
        return self._lookup(self.artists, "/artists", artist_id, _artist_entry)

    def tracklist(self, album_id: str) -> list[dict[str, Any]] | None:
        return self._lookup(self.albums, "/albums", album_id, _tracklist_entry, "/tracks?limit=50")

    def describe(self, kind: str, track_id: str | None, name: str | None) -> dict[str, Any]:
        """`image` and `url` for an artist, track or album, found through a track it plays on.
        For artists, `name` picks the right one when the track has featured artists."""
        track = self.track(track_id) if track_id else None
        if not track:
            return {}
        if kind == "track":
            return {"image": track["image"], "url": track["url"]}
        if kind == "album":
            return {"image": track["image"], "url": track["album_url"]}
        match = next((a for a in track["artists"] if a["name"] == name), None)
        artist = self.artist(match["id"]) if match else None
        return {"image": artist["image"], "url": artist["url"]} if artist else {}


# Lists that get pictures: stat name -> (kind, the field holding the name).
LISTS = {
    "top_artists": ("artist", "name"),
    "top_tracks": ("track", "name"),
    "top_albums": ("album", "name"),
    "on_repeat": ("track", "track_name"),
    "discoveries": ("artist", "artist_name"),
}
# The windows the app shows most get looked up first; past years and Wrapped last.
WINDOW_ORDER = [
    "4_weeks",
    "today",
    "this_week",
    "this_month",
    "6_months",
    "12_months",
    "this_year",
    "all_time",
]


def _rows(documents: dict[str, dict[str, Any]]) -> list[tuple[tuple, str, str, dict[str, Any]]]:
    """Every row that can have a picture, in the order to look them up: #1 of every recent
    list, then every #2, and so on, then past years."""
    found = []
    for stat_name, doc in documents.items():
        base, _, window = stat_name.partition("#")
        lists = {base: doc["data"]} if base in LISTS else {}
        if base == "wrapped":
            lists = {name: doc["data"].get(name) or [] for name in LISTS}
        if base == "artist":
            # The page's own picture, then its songs' and albums' covers.
            lists = {
                "top_artists": [doc["data"]],
                "top_tracks": doc["data"]["top_tracks"],
                "top_albums": doc["data"].get("top_albums", []),
            }
        if base == "album":
            # The cover (found through one of its tracks), then its songs' covers.
            lists = {"top_albums": [doc["data"]], "top_tracks": doc["data"]["top_tracks"]}
        past = window not in WINDOW_ORDER
        order = WINDOW_ORDER.index(window) if not past else len(WINDOW_ORDER)
        for name, rows in lists.items():
            kind, name_field = LISTS[name]
            for rank, row in enumerate(rows):
                found.append(((past, rank, order, stat_name), kind, row.get(name_field), row))
    return sorted(found, key=lambda f: f[0])


def enrich(documents: dict[str, dict[str, Any]], catalog: Catalog) -> int:
    """Add `image` and `url` to every list row the catalogue can describe, in place, then
    tracklists to album pages. Returns how many rows got a picture."""
    pictured = 0
    for _, kind, name, row in _rows(documents):
        details = catalog.describe(kind, row.get("track_id"), name)
        row.update(details)
        pictured += bool(details.get("image"))
    add_tracklists(documents, catalog)
    return pictured


def _song(name: str) -> str:
    return " ".join(name.casefold().split())


def add_tracklists(documents: dict[str, dict[str, Any]], catalog: Catalog) -> None:
    """Give each album page the album's songs in order, with your minutes and streams for
    each (0 for songs you've never played). Needs the page's album link, which `enrich` has
    just added; pages without one wait for a later run."""
    pages = [doc["data"] for name, doc in documents.items() if name.startswith("album#")]
    # Your best-ranked albums first, in case the run's lookup budget runs out.
    pages.sort(key=lambda p: min([r for r in p["ranks"].values() if r] or [10**6]))
    for page in pages:
        url = page.get("url")
        songs = catalog.tracklist(url.rstrip("/").rsplit("/", 1)[-1]) if url else None
        if not songs:
            continue
        # Plays are matched by track id, or failing that by name: the same song can have
        # different ids on a single and on the album.
        by_id = {t["track_id"]: t for t in page["top_tracks"] if t.get("track_id")}
        by_name = {_song(t["name"]): t for t in page["top_tracks"]}
        page["tracklist"] = [
            {
                "number": s["number"],
                "disc": s["disc"],
                "name": s["name"],
                "url": f"https://open.spotify.com/track/{s['id']}" if s.get("id") else None,
                "hours": played.get("hours", 0),
                "streams": played.get("streams", 0),
                # Your hours on it in each shorter range, for the range buttons.
                "hours_by_range": {
                    window: hours.get(played.get("name"), 0)
                    for window, hours in (page.get("track_hours") or {}).items()
                },
            }
            for s in songs
            for played in [by_id.get(s.get("id")) or by_name.get(_song(s["name"])) or {}]
        ]
