"""A page for each of your top albums: which songs on it you play, and since when.

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
from stats_jobs.stats import IN_WINDOW, STREAM_THRESHOLD_MS, TopRow, window_params
from stats_jobs.windows import Window

# Every song you've played on an album, up to a long deluxe edition. The catalogue later
# lines them up with the album's tracklist (stats_jobs.catalog.add_tracklists).
TOP_TRACKS = 30


@dataclass(frozen=True)
class AlbumPage:
    name: str
    artist_name: str
    minutes: float
    streams: int
    # Share of everything you've ever played, 0 to 1.
    share: float
    first_played: str
    first_track: str
    last_played: str
    # Your rank for this album in each range; None when outside its top 100.
    ranks: dict[str, int | None]
    minutes_by_month: list[Period]
    top_tracks: list[TopRow]
    # Everything you've played by the album's artist, so the page can say how much of it
    # is this album.
    artist_minutes: float = 0
    # Hours per song in the shorter ranges ("4_weeks", "6_months", "12_months"), by song
    # name, so the tracklist can be shown for a range. All time is `top_tracks` itself.
    track_hours: dict[str, dict[str, float]] | None = None
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


def album_pages(
    con: duckdb.DuckDBPyConnection, stats: dict[str, Any], windows: list[Window] = ()
) -> dict[str, AlbumPage]:
    """Every album page, keyed by stat name. `stats` is what build_documents has so far;
    `windows` are the ranges whose per-song minutes go on the page (all but all time)."""
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

    in_range: dict[tuple[str, str], dict[str, dict[str, float]]] = {}
    for window in windows:
        if window.name not in RANK_WINDOWS or window.name == "all_time":
            continue
        for album, artist, track, hours in con.execute(
            f"""
            SELECT album_name, artist_name, track_name, sum(ms_played) / 3600000.0
            FROM {plays}
            WHERE {IN_WINDOW}
            GROUP BY 1, 2, 3
            """,
            window_params(window),
        ).fetchall():
            in_range.setdefault((album, artist), {}).setdefault(window.name, {})[track] = hours

    by_artist = dict(
        con.execute(
            """
            SELECT artist_name, sum(ms_played) / 60000.0
            FROM listens
            WHERE artist_name IN (SELECT artist_name FROM page_albums)
            GROUP BY 1
            """
        ).fetchall()
    )

    pages = {}
    for album, artist, minutes, streams, first, first_track, last, track_id in summary:
        key = (album, artist)
        pages[album_stat_name(album, artist)] = AlbumPage(
            name=album,
            artist_name=artist,
            minutes=minutes,
            streams=streams,
            share=minutes / everything if everything else 0,
            first_played=first,
            first_track=first_track,
            last_played=last,
            ranks={w: ranks[w].get(key) for w in RANK_WINDOWS},
            minutes_by_month=months.get(key, []),
            top_tracks=tracks.get(key, []),
            artist_minutes=by_artist.get(artist, minutes),
            track_hours=in_range.get(key, {}),
            track_id=track_id,
        )
    return pages
