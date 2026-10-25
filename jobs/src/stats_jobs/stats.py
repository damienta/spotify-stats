"""Listening stats computed with DuckDB over a JSON Lines file of listens.

The same SQL will later run in the hourly stats Lambda, reading listens from S3 instead of disk.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import duckdb

from stats_jobs.windows import ALL_TIME, LOCAL_TZ, Window

# Spotify counts a stream once at least 30 seconds have been played.
STREAM_THRESHOLD_MS = 30_000


def in_window(column: str = "played_at") -> str:
    """SQL condition restricting `column` to a `Window`; bind its bounds with `window_params`."""
    return (
        f"{column} >= coalesce($start::TIMESTAMPTZ, '-infinity'::TIMESTAMPTZ) "
        f"AND {column} < coalesce($end::TIMESTAMPTZ, 'infinity'::TIMESTAMPTZ)"
    )


IN_WINDOW = in_window()


def window_params(window: Window, **extra: object) -> dict[str, object]:
    return {"start": window.start, "end": window.end, **extra}


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


# The Listen schema (stats_ingest.listen) as DuckDB types, so JSON Lines files written by
# different versions or sources always read the same way.
LISTEN_COLUMNS = {
    "listen_id": "VARCHAR",
    "user_id": "VARCHAR",
    "played_at": "TIMESTAMPTZ",
    "track_id": "VARCHAR",
    "track_name": "VARCHAR",
    "artist_name": "VARCHAR",
    "album_name": "VARCHAR",
    "source": "VARCHAR",
    "ms_played": "BIGINT",
    "skipped": "BOOLEAN",
    "shuffle": "BOOLEAN",
    "platform": "VARCHAR",
    "reason_start": "VARCHAR",
    "reason_end": "VARCHAR",
    "track_duration_ms": "BIGINT",
}


def _sql_list(paths: list[Path]) -> str:
    return "[" + ", ".join("'" + str(p).replace("'", "''") + "'" for p in paths) + "]"


def _source_sql(paths: list[Path]) -> str:
    """SQL reading every listens file, Parquet and JSON Lines alike, as one table."""
    parquet = [p for p in paths if p.suffix == ".parquet"]
    json_lines = [p for p in paths if p.suffix != ".parquet"]
    columns = "{" + ", ".join(f"'{k}': '{v}'" for k, v in LISTEN_COLUMNS.items()) + "}"
    parts = []
    if parquet:
        parts.append(f"SELECT * FROM read_parquet({_sql_list(parquet)}, union_by_name = true)")
    if json_lines:
        parts.append(
            f"SELECT * FROM read_json({_sql_list(json_lines)}, "
            f"format = 'newline_delimited', columns = {columns})"
        )
    return " UNION ALL BY NAME ".join(parts)


def connect(listens: Path | Sequence[Path], materialize: bool = False) -> duckdb.DuckDBPyConnection:
    """Open an in-memory DuckDB with the listens exposed as a `listens` view.

    `listens` is one file or several, each Parquet or JSON Lines. The view keeps one row per
    `listen_id`, so duplicates that reached storage are never counted twice (ADR 0003). When a
    play exists from both sources, the export row wins because it carries more detail. It also
    adds `played_at_local`, the play's time on the listener's clock, and estimates
    `ms_played` for API plays as the track's full length.

    With `materialize`, the deduplicated listens are loaded into memory once instead of being
    re-read for every query: worth it when running many queries.
    """
    paths = [listens] if isinstance(listens, Path) else list(listens)
    if not paths:
        raise ValueError("no listens files to read")
    con = duckdb.connect()
    con.execute("SET TimeZone = 'UTC'")
    con.execute(
        f"""
        CREATE {"TABLE" if materialize else "VIEW"} listens AS
        SELECT
            * REPLACE (
                played_at::TIMESTAMPTZ AS played_at,
                -- The API doesn't report time listened: count its plays as heard in full.
                coalesce(ms_played::BIGINT, track_duration_ms::BIGINT) AS ms_played
            ),
            timezone('{LOCAL_TZ.key}', played_at::TIMESTAMPTZ) AS played_at_local
        FROM ({_source_sql(paths)})
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
        window_params(window, threshold=STREAM_THRESHOLD_MS),
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
        -- Sort on whole milliseconds: summed floats can differ in the last digit between runs.
        ORDER BY streams DESC, sum(ms_played) DESC, name, artist
        LIMIT $limit
        """,
        window_params(window, threshold=STREAM_THRESHOLD_MS, limit=limit),
    ).fetchall()
    return [TopRow(*r) for r in rows]
