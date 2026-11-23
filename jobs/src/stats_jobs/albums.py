"""A page for each of your top albums: which songs on it you play, since when, and when.

Like the artist pages (stats_jobs.artists): built for the top `PAGES_FROM_EACH` albums of
every range the Top tab shows, each its own stats item keyed by
`stats_ingest.storage.album_stat_name`, so the API reads one small item per page.

An album is its name plus its artist, the same key the top albums list uses.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import duckdb

from stats_ingest.storage import album_stat_name
from stats_jobs.artists import PAGES_FROM_EACH, RANK_WINDOWS
from stats_jobs.habits import Period
from stats_jobs.stats import STREAM_THRESHOLD_MS, TopRow

# Albums are short, so show every song you've played on one, up to a long deluxe edition.
TOP_TRACKS = 30
# The same hours as the listening clock's parts on the web (ListeningClock.tsx).
PARTS = {"Night": (0, 6), "Morning": (6, 12), "Afternoon": (12, 18), "Evening": (18, 24)}


@dataclass(frozen=True)
class AlbumPage:
    name: str
    artist_name: str
    minutes: float
    streams: int
    tracks: int
    # Share of everything you've ever played, 0 to 1.
    share: float
    first_played: str
    first_track: str
    last_played: str
    # Your rank for this album in each range; None when outside its top 100.
    ranks: dict[str, int | None]
    minutes_by_month: list[Period]
    top_tracks: list[TopRow]
    # The day you played it most, on your own clock.
    biggest_day: Period | None
    # Minutes in each part of the day, PARTS order.
    time_of_day: dict[str, float]
    # One of its tracks: how stats_jobs.catalog finds the cover and the album's link.
    track_id: str | None = None


def page_albums(stats: dict[str, Any]) -> list[tuple[str, str]]:
    """Which albums get a page, as (album, artist): the top albums of every range,
    best-ranked first, once each."""
    keys: dict[tuple[str, str], None] = {}
    for window in RANK_WINDOWS:
        for row in stats.get(f"top_albums#{window}", [])[:PAGES_FROM_EACH]:
            keys.setdefault((row.name, row.artist_name))
    return list(keys)


def album_pages(con: duckdb.DuckDBPyConnection, stats: dict[str, Any]) -> dict[str, AlbumPage]:
    """Every album page, keyed by stat name. `stats` is what build_documents has so far."""
    keys = page_albums(stats)
    if not keys:
        return {}
    everything = stats["totals#all_time"].hours * 60
    ranks = {
        window: {
            (row.name, row.artist_name): n
            for n, row in enumerate(stats.get(f"top_albums#{window}", []), 1)
        }
        for window in RANK_WINDOWS
    }
    # The albums as a small table to join on: matching two columns at once is simpler and
    # faster as a join than as a list filter.
    con.execute(
        "CREATE OR REPLACE TEMP TABLE page_albums AS "
        "SELECT unnest($albums) AS album_name, unnest($artists) AS artist_name",
        {"albums": [a for a, _ in keys], "artists": [r for _, r in keys]},
    )
    plays = "listens JOIN page_albums USING (album_name, artist_name)"
    threshold = {"threshold": STREAM_THRESHOLD_MS}

    summary = con.execute(
        f"""
        SELECT
            album_name,
            artist_name,
            sum(ms_played) / 60000.0,
            count(*) FILTER (WHERE ms_played >= $threshold),
            count(DISTINCT track_name),
            min(played_at_local)::VARCHAR,
            arg_min(track_name, played_at),
            max(played_at_local)::VARCHAR,
            first(track_id ORDER BY ms_played DESC, track_id) FILTER (WHERE track_id IS NOT NULL)
        FROM {plays}
        GROUP BY album_name, artist_name
        """,
        threshold,
    ).fetchall()

    months: dict[tuple[str, str], list[Period]] = {}
    for album, artist, start, minutes in con.execute(
        f"""
        SELECT album_name, artist_name, date_trunc('month', played_at_local)::DATE,
            sum(ms_played) / 60000.0
        FROM {plays}
        GROUP BY 1, 2, 3
        ORDER BY 1, 2, 3
        """
    ).fetchall():
        months.setdefault((album, artist), []).append(Period(start, minutes))

    tracks: dict[tuple[str, str], list[TopRow]] = {}
    for album, artist, track, streams, hours, track_id in con.execute(
        f"""
        SELECT
            album_name,
            artist_name,
            track_name,
            count(*) FILTER (WHERE ms_played >= $threshold) AS streams,
            sum(ms_played) / 3600000.0,
            first(track_id ORDER BY ms_played DESC, track_id) FILTER (WHERE track_id IS NOT NULL)
        FROM {plays}
        GROUP BY album_name, artist_name, track_name
        QUALIFY row_number() OVER (
            PARTITION BY album_name, artist_name
            ORDER BY sum(ms_played) DESC, streams DESC, track_name
        ) <= $limit
        ORDER BY album_name, artist_name, sum(ms_played) DESC, streams DESC, track_name
        """,
        {**threshold, "limit": TOP_TRACKS},
    ).fetchall():
        row = TopRow(track, artist, streams, hours, track_id)
        tracks.setdefault((album, artist), []).append(row)

    biggest: dict[tuple[str, str], Period] = {
        (album, artist): Period(day, minutes)
        for album, artist, day, minutes in con.execute(
            f"""
            SELECT album_name, artist_name, played_at_local::DATE AS day, sum(ms_played) / 60000.0
            FROM {plays}
            GROUP BY album_name, artist_name, day
            QUALIFY row_number() OVER (
                PARTITION BY album_name, artist_name ORDER BY sum(ms_played) DESC, day
            ) = 1
            """
        ).fetchall()
    }

    parts: dict[tuple[str, str], dict[str, float]] = {}
    for album, artist, hour, minutes in con.execute(
        f"""
        SELECT album_name, artist_name, hour(played_at_local), sum(ms_played) / 60000.0
        FROM {plays}
        GROUP BY 1, 2, 3
        """
    ).fetchall():
        split = parts.setdefault((album, artist), dict.fromkeys(PARTS, 0.0))
        part = next(name for name, (start, end) in PARTS.items() if start <= hour < end)
        split[part] += minutes

    pages = {}
    for album, artist, minutes, streams, n_tracks, first, first_track, last, track_id in summary:
        key = (album, artist)
        pages[album_stat_name(album, artist)] = AlbumPage(
            name=album,
            artist_name=artist,
            minutes=minutes,
            streams=streams,
            tracks=n_tracks,
            share=minutes / everything if everything else 0,
            first_played=first,
            first_track=first_track,
            last_played=last,
            ranks={w: ranks[w].get(key) for w in RANK_WINDOWS},
            minutes_by_month=months.get(key, []),
            top_tracks=tracks.get(key, []),
            biggest_day=biggest.get(key),
            time_of_day=parts.get(key, dict.fromkeys(PARTS, 0.0)),
            track_id=track_id,
        )
    return pages
