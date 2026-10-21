"""Listening stats computed with DuckDB over a JSON Lines file of listens.

The same SQL will later run in the hourly stats Lambda, reading listens from S3 instead of disk.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import duckdb

from stats_jobs.windows import ALL_TIME, LOCAL_TZ, Window

# Spotify counts a stream once at least 30 seconds have been played.
STREAM_THRESHOLD_MS = 30_000

# Restricts a query to a `Window`; bind its bounds with `window_params`.
IN_WINDOW = (
    "played_at >= coalesce($start::TIMESTAMPTZ, '-infinity'::TIMESTAMPTZ) "
    "AND played_at < coalesce($end::TIMESTAMPTZ, 'infinity'::TIMESTAMPTZ)"
)


def window_params(window: Window, **extra: object) -> dict[str, object]:
    return {"start": window.start, "end": window.end, "threshold": STREAM_THRESHOLD_MS, **extra}


@dataclass(frozen=True)
class Totals:
    streams: int
    hours: float
    artists: int
    tracks: int
    first_played: str
    last_played: str


Kind = Literal["artist", "track", "album"]

# What one row of each top list is. Tracks are keyed by name and artist rather than track_id,
# so the single and album releases of the same song count as one track.
TOP_COLUMNS: dict[Kind, tuple[str, str]] = {
    "artist": ("artist_name", "NULL"),
    "track": ("track_name", "artist_name"),
    "album": ("album_name", "artist_name"),
}


@dataclass(frozen=True)
class TopRow:
    name: str
    artist_name: str | None
    streams: int
    hours: float


def connect(listens: Path) -> duckdb.DuckDBPyConnection:
    """Open an in-memory DuckDB with the listens file exposed as a `listens` view.

    `listens` may be Parquet or JSON Lines. The view keeps one row per `listen_id`, so
    duplicates that reached storage are never counted twice (ADR 0003). When a play exists
    from both sources, the export row wins because it carries more detail. It also adds
    `played_at_local`, the play's time on the listener's clock.
    """
    con = duckdb.connect()
    con.execute("SET TimeZone = 'UTC'")
    if listens.suffix == ".parquet":
        source = con.read_parquet(str(listens))
    else:
        source = con.read_json(str(listens), format="newline_delimited")
    source.create_view("listens_raw")
    con.execute(
        f"""
        CREATE VIEW listens AS
        SELECT
            * REPLACE (played_at::TIMESTAMPTZ AS played_at),
            timezone('{LOCAL_TZ.key}', played_at::TIMESTAMPTZ) AS played_at_local
        FROM listens_raw
        QUALIFY row_number() OVER (PARTITION BY listen_id ORDER BY source = 'export' DESC) = 1
        """
    )
    return con


def write_parquet(con: duckdb.DuckDBPyConnection, dest: Path) -> int:
    """Write the deduplicated listens to a Parquet file, oldest first. Returns the row count."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    con.sql("SELECT * EXCLUDE (played_at_local) FROM listens ORDER BY played_at").write_parquet(
        str(dest), compression="zstd"
    )
    return con.execute("SELECT count(*) FROM listens").fetchone()[0]


def totals(con: duckdb.DuckDBPyConnection, window: Window = ALL_TIME) -> Totals:
    row = con.execute(
        f"""
        SELECT
            count(*) FILTER (WHERE ms_played >= $threshold),
            coalesce(sum(ms_played), 0) / 3600000.0,
            count(DISTINCT artist_name),
            count(DISTINCT track_id),
            coalesce(min(played_at_local)::VARCHAR, ''),
            coalesce(max(played_at_local)::VARCHAR, '')
        FROM listens
        WHERE {IN_WINDOW}
        """,
        window_params(window),
    ).fetchone()
    return Totals(*row)


def top(
    con: duckdb.DuckDBPyConnection, kind: Kind, limit: int = 10, window: Window = ALL_TIME
) -> list[TopRow]:
    """Most-streamed artists, tracks or albums in a window. Ties go to more hours played."""
    name, artist = TOP_COLUMNS[kind]
    rows = con.execute(
        f"""
        SELECT
            {name} AS name,
            {artist} AS artist,
            count(*) FILTER (WHERE ms_played >= $threshold) AS streams,
            sum(ms_played) / 3600000.0 AS hours
        FROM listens
        WHERE {IN_WINDOW}
        GROUP BY ALL
        ORDER BY streams DESC, hours DESC, name
        LIMIT $limit
        """,
        window_params(window, limit=limit),
    ).fetchall()
    return [TopRow(*r) for r in rows]
