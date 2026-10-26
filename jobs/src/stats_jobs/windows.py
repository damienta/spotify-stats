"""Time windows the stats are computed over, matching what stats apps show."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Plays are stored in UTC; anything about days, hours or years uses the listener's clock.
LOCAL_TZ = ZoneInfo("Europe/London")


@dataclass(frozen=True)
class Window:
    """Plays with `start <= played_at < end`. A missing bound is open-ended."""

    name: str
    start: datetime | None = None
    end: datetime | None = None


ALL_TIME = Window("all_time")


def rolling(name: str, now: datetime, days: int) -> Window:
    return Window(name, start=now - timedelta(days=days), end=now)


def calendar(name: str, now: datetime) -> Window:
    """Today, this week (from Monday), this month or this year so far, on the listener's clock."""
    local = now.astimezone(LOCAL_TZ)
    midnight = local.replace(hour=0, minute=0, second=0, microsecond=0)
    starts = {
        "today": midnight,
        "this_week": midnight - timedelta(days=local.weekday()),
        "this_month": midnight.replace(day=1),
        "this_year": midnight.replace(month=1, day=1),
    }
    return Window(name, start=starts[name], end=now)


CALENDAR_WINDOWS = ("today", "this_week", "this_month", "this_year")


def standard_windows(now: datetime) -> list[Window]:
    """The windows every stat is published for: 4 weeks, 6 months, 12 months, all time, and
    today, this week, this month and this year so far."""
    return [
        rolling("4_weeks", now, 28),
        rolling("6_months", now, 182),
        rolling("12_months", now, 365),
        ALL_TIME,
        *(calendar(name, now) for name in CALENDAR_WINDOWS),
    ]


def year(y: int) -> Window:
    """A calendar year on the listener's clock."""
    return Window(
        f"year_{y}",
        start=datetime(y, 1, 1, tzinfo=LOCAL_TZ),
        end=datetime(y + 1, 1, 1, tzinfo=LOCAL_TZ),
    )


def by_name(name: str, now: datetime) -> Window:
    if name.startswith("year_"):
        return year(int(name.removeprefix("year_")))
    for window in standard_windows(now):
        if window.name == name:
            return window
    raise ValueError(f"unknown window: {name!r}")
