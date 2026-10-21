"""Every stat as a JSON document, shaped like the items of the DynamoDB `stats` table.

Each document is keyed by `stat_name` (for example `top_artists#4_weeks`) and is ready for the
API to return as is. Building them is the whole job; item 8 only changes where they're saved.
"""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from typing import Any

import duckdb

from stats_jobs.behaviour import discoveries, most_skipped, on_repeat, skip_rate
from stats_jobs.habits import listening_clock, minutes_by, streaks
from stats_jobs.stats import top, totals
from stats_jobs.windows import LOCAL_TZ, Window, standard_windows, year

TOP_LIMIT = 50
# DynamoDB items max out at 400 KB; stay well clear.
MAX_DOCUMENT_BYTES = 300_000


def years_listened(con: duckdb.DuckDBPyConnection) -> list[int]:
    return [
        y
        for (y,) in con.execute(
            "SELECT DISTINCT year(played_at_local) FROM listens ORDER BY 1"
        ).fetchall()
    ]


def window_stats(con: duckdb.DuckDBPyConnection, window: Window) -> dict[str, Any]:
    """Every per-window stat, keyed by stat name without the window suffix."""
    # Daily detail for short windows; months for long ones so documents stay small.
    grain = "day" if window.name in ("4_weeks", "6_months") else "month"
    return {
        "totals": totals(con, window),
        "top_artists": top(con, "artist", TOP_LIMIT, window),
        "top_tracks": top(con, "track", TOP_LIMIT, window),
        "top_albums": top(con, "album", TOP_LIMIT, window),
        f"minutes_by_{grain}": minutes_by(con, grain, window),
        "listening_clock": listening_clock(con, window),
        "skips": {
            "skip_rate": skip_rate(con, window),
            "most_skipped_artists": most_skipped(con, "artist", window),
        },
        "discoveries": discoveries(con, window, limit=20),
        "on_repeat": on_repeat(con, window, limit=10),
    }


def wrapped(con: duckdb.DuckDBPyConnection, y: int) -> dict[str, Any]:
    """A personal Wrapped for one calendar year."""
    window = year(y)
    months = minutes_by(con, "month", window)
    t = totals(con, window)
    return {
        "year": y,
        "totals": t,
        "minutes": round(t.hours * 60),
        "top_artists": top(con, "artist", 5, window),
        "top_tracks": top(con, "track", 5, window),
        "top_albums": top(con, "album", 5, window),
        "top_month": max(months, key=lambda p: p.minutes) if months else None,
        "discoveries": discoveries(con, window, limit=5),
        "on_repeat": on_repeat(con, window, limit=1),
        "skip_rate": skip_rate(con, window),
    }


def build_documents(
    con: duckdb.DuckDBPyConnection, user_id: str, now: datetime
) -> dict[str, dict[str, Any]]:
    stats: dict[str, Any] = {}
    windows = standard_windows(now) + [year(y) for y in years_listened(con)]
    for window in windows:
        for name, data in window_stats(con, window).items():
            stats[f"{name}#{window.name}"] = data
    stats["streaks"] = streaks(con, today=now.astimezone(LOCAL_TZ).date())
    for y in years_listened(con):
        stats[f"wrapped#{y}"] = wrapped(con, y)

    generated_at = now.isoformat()
    documents = {
        stat_name: {
            "user_id": user_id,
            "stat_name": stat_name,
            "generated_at": generated_at,
            "data": to_json(data),
        }
        for stat_name, data in stats.items()
    }
    for stat_name, doc in documents.items():
        size = len(json.dumps(doc).encode())
        if size > MAX_DOCUMENT_BYTES:
            raise ValueError(f"{stat_name} is {size:,} bytes, over {MAX_DOCUMENT_BYTES:,}")
    return documents


def to_json(value: Any) -> Any:
    """Dataclasses, dates and floats to plain JSON values."""
    if is_dataclass(value):
        return to_json(asdict(value))
    if isinstance(value, dict):
        return {k: to_json(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [to_json(v) for v in value]
    if isinstance(value, date | datetime):
        return value.isoformat()
    if isinstance(value, float):
        return round(value, 4)
    return value
