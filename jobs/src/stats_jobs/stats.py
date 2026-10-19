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
    """Open an in-memory DuckDB with the listens file exposed as a `listens` view."""
    con = duckdb.connect()
    con.read_json(str(listens), format="newline_delimited").create_view("listens")
    return con


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
