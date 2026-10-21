"""Listening stats computed with DuckDB over a JSON Lines file of listens.

The same SQL will later run in the hourly stats Lambda, reading listens from S3 instead of disk.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import duckdb

# Spotify counts a stream once at least 30 seconds have been played.
STREAM_THRESHOLD_MS = 30_000


@dataclass(frozen=True)
class Totals:
    streams: int
    hours: float
    artists: int
    tracks: int
    first_played: str
    last_played: str


@dataclass(frozen=True)
class ArtistRow:
    artist_name: str
    streams: int
    hours: float


def connect(listens: Path) -> duckdb.DuckDBPyConnection:
    """Open an in-memory DuckDB with the listens file exposed as a `listens` view.

    `listens` may be Parquet or JSON Lines. The view keeps one row per `listen_id`, so
    duplicates that reached storage are never counted twice (ADR 0003). When a play exists
    from both sources, the export row wins because it carries more detail.
    """
    con = duckdb.connect()
    con.execute("SET TimeZone = 'UTC'")
    if listens.suffix == ".parquet":
        source = con.read_parquet(str(listens))
    else:
        source = con.read_json(str(listens), format="newline_delimited")
    source.create_view("listens_raw")
    con.execute(
        """
        CREATE VIEW listens AS
        SELECT * REPLACE (played_at::TIMESTAMPTZ AS played_at)
        FROM listens_raw
        QUALIFY row_number() OVER (PARTITION BY listen_id ORDER BY source = 'export' DESC) = 1
        """
    )
    return con


def write_parquet(con: duckdb.DuckDBPyConnection, dest: Path) -> int:
    """Write the deduplicated listens to a Parquet file, oldest first. Returns the row count."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    con.sql("SELECT * FROM listens ORDER BY played_at").write_parquet(str(dest), compression="zstd")
    return con.execute("SELECT count(*) FROM listens").fetchone()[0]


def totals(con: duckdb.DuckDBPyConnection) -> Totals:
    row = con.execute(
        """
        SELECT
            count(*) FILTER (WHERE ms_played >= $threshold),
            coalesce(sum(ms_played), 0) / 3600000.0,
            count(DISTINCT artist_name),
            count(DISTINCT track_id),
            min(played_at)::VARCHAR,
            max(played_at)::VARCHAR
        FROM listens
        """,
        {"threshold": STREAM_THRESHOLD_MS},
    ).fetchone()
    return Totals(*row)


def top_artists(con: duckdb.DuckDBPyConnection, limit: int = 10) -> list[ArtistRow]:
    rows = con.execute(
        """
        SELECT
            artist_name,
            count(*) FILTER (WHERE ms_played >= $threshold) AS streams,
            sum(ms_played) / 3600000.0 AS hours
        FROM listens
        GROUP BY artist_name
        ORDER BY streams DESC, hours DESC, artist_name
        LIMIT $limit
        """,
        {"threshold": STREAM_THRESHOLD_MS, "limit": limit},
    ).fetchall()
    return [ArtistRow(*r) for r in rows]
