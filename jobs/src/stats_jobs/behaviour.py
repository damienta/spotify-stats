"""How someone listens: what they skip, what they discover and what they put on repeat.

A skip is a play that ended before 30 seconds, the flip side of a stream. Spotify's own
`skipped` flag is not used: exports leave it false for every play before 2022, so it would
make older years look skip-free.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import duckdb

from stats_jobs.stats import (
    IN_WINDOW,
    STREAM_THRESHOLD_MS,
    TOP_COLUMNS,
    Kind,
    in_window,
    window_params,
)
from stats_jobs.windows import ALL_TIME, Window


@dataclass(frozen=True)
class SkipRow:
    name: str
    artist_name: str | None
    plays: int
    skip_rate: float


@dataclass(frozen=True)
class Discovery:
    artist_name: str
    first_played: date
    streams: int


@dataclass(frozen=True)
class Repeat:
    track_name: str
    artist_name: str
    day: date
    streams: int


def skip_rate(con: duckdb.DuckDBPyConnection, window: Window = ALL_TIME) -> float | None:
    """Share of plays that were skips, or None when the window has no plays with a duration."""
    return con.execute(
        f"""
        SELECT avg((ms_played < $threshold)::INTEGER)
        FROM listens
        WHERE {IN_WINDOW} AND ms_played IS NOT NULL
        """,
        window_params(window, threshold=STREAM_THRESHOLD_MS),
    ).fetchone()[0]


def most_skipped(
    con: duckdb.DuckDBPyConnection,
    kind: Kind,
    window: Window = ALL_TIME,
    min_plays: int = 20,
    limit: int = 10,
) -> list[SkipRow]:
    """Artists, tracks or albums skipped most often, among those played at least `min_plays`."""
    name, artist = TOP_COLUMNS[kind]
    rows = con.execute(
        f"""
        SELECT {name}, {artist}, count(*) AS plays, avg((ms_played < $threshold)::INTEGER) AS rate
        FROM listens
        WHERE {IN_WINDOW} AND ms_played IS NOT NULL
        GROUP BY ALL
        HAVING count(*) >= $min_plays
        ORDER BY rate DESC, plays DESC, 1, 2
        LIMIT $limit
        """,
        window_params(window, threshold=STREAM_THRESHOLD_MS, min_plays=min_plays, limit=limit),
    ).fetchall()
    return [SkipRow(*r) for r in rows]


def discoveries(
    con: duckdb.DuckDBPyConnection, window: Window = ALL_TIME, limit: int = 10
) -> list[Discovery]:
    """Artists first streamed inside the window, ranked by how much they've been streamed since.

    Over all time this is simply when each top artist was first heard.
    """
    rows = con.execute(
        f"""
        WITH artists AS (
            SELECT artist_name, min(played_at) AS first_at, min(played_at_local)::DATE AS first_day,
                   count(*) AS streams
            FROM listens
            WHERE ms_played >= $threshold
            GROUP BY artist_name
        )
        SELECT artist_name, first_day, streams
        FROM artists
        WHERE {in_window("first_at")}
        ORDER BY streams DESC, artist_name
        LIMIT $limit
        """,
        window_params(window, threshold=STREAM_THRESHOLD_MS, limit=limit),
    ).fetchall()
    return [Discovery(*r) for r in rows]


def new_artists_by_month(
    con: duckdb.DuckDBPyConnection, window: Window = ALL_TIME
) -> list[tuple[date, int]]:
    """How many artists were streamed for the first time each month."""
    return con.execute(
        f"""
        WITH firsts AS (
            SELECT min(played_at) AS first_at, min(played_at_local) AS first_local
            FROM listens
            WHERE ms_played >= $threshold
            GROUP BY artist_name
        )
        SELECT date_trunc('month', first_local)::DATE, count(*)
        FROM firsts
        WHERE {in_window("first_at")}
        GROUP BY 1
        ORDER BY 1
        """,
        window_params(window, threshold=STREAM_THRESHOLD_MS),
    ).fetchall()


def on_repeat(
    con: duckdb.DuckDBPyConnection, window: Window = ALL_TIME, limit: int = 10
) -> list[Repeat]:
    """The most times a single track was streamed in one day."""
    rows = con.execute(
        f"""
        SELECT track_name, artist_name, played_at_local::DATE AS day, count(*) AS streams
        FROM listens
        WHERE {IN_WINDOW} AND ms_played >= $threshold
        GROUP BY ALL
        ORDER BY streams DESC, day DESC, track_name, artist_name
        LIMIT $limit
        """,
        window_params(window, threshold=STREAM_THRESHOLD_MS, limit=limit),
    ).fetchall()
    return [Repeat(*r) for r in rows]
