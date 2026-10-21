"""When someone listens: minutes over time, the listening clock and daily streaks.

Everything here uses `played_at_local`, the listener's clock. For export plays that is when
playback stopped, so a long play counts towards the hour it ended in.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal

import duckdb

from stats_jobs.stats import IN_WINDOW, STREAM_THRESHOLD_MS, window_params
from stats_jobs.windows import ALL_TIME, Window

Grain = Literal["day", "week", "month"]


@dataclass(frozen=True)
class Period:
    start: date
    minutes: float


@dataclass(frozen=True)
class ClockCell:
    weekday: int  # 0 = Monday
    hour: int
    minutes: float


@dataclass(frozen=True)
class Streak:
    days: int
    start: date | None
    end: date | None


@dataclass(frozen=True)
class Streaks:
    current: Streak
    longest: Streak


def minutes_by(
    con: duckdb.DuckDBPyConnection, grain: Grain, window: Window = ALL_TIME
) -> list[Period]:
    """Minutes played per day, week (starting Monday) or month, oldest first."""
    rows = con.execute(
        f"""
        SELECT date_trunc($grain, played_at_local)::DATE, sum(ms_played) / 60000.0
        FROM listens
        WHERE {IN_WINDOW}
        GROUP BY 1
        ORDER BY 1
        """,
        window_params(window, grain=grain),
    ).fetchall()
    return [Period(*r) for r in rows]


def listening_clock(con: duckdb.DuckDBPyConnection, window: Window = ALL_TIME) -> list[ClockCell]:
    """Minutes played in each weekday and hour: all 168 cells, Monday 00:00 first."""
    rows = con.execute(
        f"""
        WITH played AS (
            SELECT isodow(played_at_local) - 1 AS weekday, hour(played_at_local) AS hour,
                   sum(ms_played) / 60000.0 AS minutes
            FROM listens
            WHERE {IN_WINDOW}
            GROUP BY ALL
        )
        SELECT d.weekday, h.hour, coalesce(p.minutes, 0)
        FROM range(7) AS d(weekday)
        CROSS JOIN range(24) AS h(hour)
        LEFT JOIN played AS p USING (weekday, hour)
        ORDER BY 1, 2
        """,
        window_params(window),
    ).fetchall()
    return [ClockCell(*r) for r in rows]


def streaks(con: duckdb.DuckDBPyConnection, today: date) -> Streaks:
    """Runs of consecutive days with at least one stream.

    The current streak is the run that ends today or yesterday, so it isn't broken just
    because today's listening hasn't happened yet.
    """
    rows = con.execute(
        """
        WITH days AS (
            SELECT DISTINCT played_at_local::DATE AS day
            FROM listens
            WHERE ms_played >= $threshold
        ),
        runs AS (
            -- Consecutive days share the same day minus row number: the gaps-and-islands trick.
            SELECT day, day - (row_number() OVER (ORDER BY day))::INTEGER AS run
            FROM days
        )
        SELECT count(*) AS days, min(day), max(day)
        FROM runs
        GROUP BY run
        ORDER BY days DESC, max(day) DESC
        """,
        {"threshold": STREAM_THRESHOLD_MS},
    ).fetchall()
    runs = [Streak(*r) for r in rows]
    none = Streak(0, None, None)
    current = next((r for r in runs if r.end and (today - r.end).days <= 1), none)
    return Streaks(current=current, longest=runs[0] if runs else none)
