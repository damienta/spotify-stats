"""A page for each of your top artists: how much, since when, which songs, month by month.

Pages are built for the top `PAGES_FROM_EACH` artists of every range the Top tab shows, so
any artist you can tap there has one. Each is its own stats item, keyed by
`stats_ingest.storage.artist_stat_name`, so the API reads one small item per page.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import duckdb

from stats_ingest.storage import artist_stat_name
from stats_jobs.habits import Period
from stats_jobs.stats import STREAM_THRESHOLD_MS, TopRow

# The Top tab's ranges, in the order the page shows your rank in them.
RANK_WINDOWS = ("4_weeks", "6_months", "12_months", "all_time")
PAGES_FROM_EACH = 50
TOP_TRACKS = 10


@dataclass(frozen=True)
class ArtistPage:
    name: str
    minutes: float
    streams: int
    tracks: int
    # Share of everything you've ever played, 0 to 1.
    share: float
    first_played: str
    first_track: str
    last_played: str
    # Your rank for this artist in each range; None when outside its top 100.
    ranks: dict[str, int | None]
    minutes_by_month: list[Period]
    top_tracks: list[TopRow]
    # One of their tracks: how stats_jobs.catalog finds the artist's picture and link.
    track_id: str | None = None


def page_artists(stats: dict[str, Any]) -> list[str]:
    """Who gets a page: the top artists of every range, best-ranked first, once each."""
    names: dict[str, None] = {}
    for window in RANK_WINDOWS:
        for row in stats.get(f"top_artists#{window}", [])[:PAGES_FROM_EACH]:
            names.setdefault(row.name)
    return list(names)


def artist_pages(con: duckdb.DuckDBPyConnection, stats: dict[str, Any]) -> dict[str, ArtistPage]:
    """Every artist page, keyed by stat name. `stats` is what build_documents has so far."""
    names = page_artists(stats)
    if not names:
        return {}
    params = {"names": names, "threshold": STREAM_THRESHOLD_MS}
    everything = stats["totals#all_time"].hours * 60
    ranks = {
        window: {row.name: n for n, row in enumerate(stats.get(f"top_artists#{window}", []), 1)}
        for window in RANK_WINDOWS
    }

    summary = con.execute(
        """
        SELECT
            artist_name,
            sum(ms_played) / 60000.0,
            count(*) FILTER (WHERE ms_played >= $threshold),
            count(DISTINCT track_name),
            min(played_at_local)::VARCHAR,
            arg_min(track_name, played_at),
            max(played_at_local)::VARCHAR,
            first(track_id ORDER BY ms_played DESC, track_id) FILTER (WHERE track_id IS NOT NULL)
        FROM listens
        WHERE list_contains($names, artist_name)
        GROUP BY artist_name
        """,
        params,
    ).fetchall()

    months: dict[str, list[Period]] = {}
    for name, start, minutes in con.execute(
        """
        SELECT artist_name, date_trunc('month', played_at_local)::DATE, sum(ms_played) / 60000.0
        FROM listens
        WHERE list_contains($names, artist_name)
        GROUP BY 1, 2
        ORDER BY 1, 2
        """,
        {"names": names},
    ).fetchall():
        months.setdefault(name, []).append(Period(start, minutes))

    # Tracks keyed by name, like the top tracks list (stats_jobs.stats.TOP_COLUMNS).
    tracks: dict[str, list[TopRow]] = {}
    for name, track, streams, hours, track_id in con.execute(
        """
        SELECT
            artist_name,
            track_name,
            count(*) FILTER (WHERE ms_played >= $threshold) AS streams,
            sum(ms_played) / 3600000.0,
            first(track_id ORDER BY ms_played DESC, track_id) FILTER (WHERE track_id IS NOT NULL)
        FROM listens
        WHERE list_contains($names, artist_name)
        GROUP BY artist_name, track_name
        QUALIFY row_number() OVER (
            PARTITION BY artist_name ORDER BY sum(ms_played) DESC, streams DESC, track_name
        ) <= $limit
        ORDER BY artist_name, sum(ms_played) DESC, streams DESC, track_name
        """,
        {**params, "limit": TOP_TRACKS},
    ).fetchall():
        tracks.setdefault(name, []).append(TopRow(track, name, streams, hours, track_id))

    pages = {}
    for name, minutes, streams, n_tracks, first, first_track, last, track_id in summary:
        pages[artist_stat_name(name)] = ArtistPage(
            name=name,
            minutes=minutes,
            streams=streams,
            tracks=n_tracks,
            share=minutes / everything if everything else 0,
            first_played=first,
            first_track=first_track,
            last_played=last,
            ranks={w: ranks[w].get(name) for w in RANK_WINDOWS},
            minutes_by_month=months.get(name, []),
            top_tracks=tracks.get(name, []),
            track_id=track_id,
        )
    return pages
