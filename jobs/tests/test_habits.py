import json
from datetime import date, datetime

import pytest

from stats_jobs.habits import listening_clock, minutes_by, streaks
from stats_jobs.stats import connect
from stats_jobs.windows import year


def listen(played_at, ms_played=60_000):
    return {
        "listen_id": played_at,
        "user_id": "u1",
        "played_at": played_at,
        "track_id": "t",
        "track_name": "Song",
        "artist_name": "A",
        "album_name": "Album",
        "source": "export",
        "ms_played": ms_played,
    }


def connect_rows(tmp_path, played_at, **kwargs):
    path = tmp_path / "listens.jsonl"
    path.write_text("\n".join(json.dumps(listen(p, **kwargs)) for p in played_at))
    return connect(path)


@pytest.fixture
def con(tmp_path):
    return connect_rows(
        tmp_path,
        [
            "2024-01-30T09:00:00Z",  # Tuesday
            "2024-01-31T09:00:00Z",
            "2024-02-01T09:00:00Z",
            "2024-02-01T21:00:00Z",
            "2024-02-02T09:00:00Z",
            "2024-02-10T09:00:00Z",
            "2024-02-11T09:00:00Z",
        ],
    )


def test_minutes_by_day_week_and_month(con):
    assert [(p.start, p.minutes) for p in minutes_by(con, "month")] == [
        (date(2024, 1, 1), 2.0),
        (date(2024, 2, 1), 5.0),
    ]
    weeks = minutes_by(con, "week")
    assert weeks[0].start == date(2024, 1, 29)  # weeks start on Monday
    day = minutes_by(con, "day")[2]
    assert (day.start, day.minutes) == (date(2024, 2, 1), 2.0)


def test_minutes_by_hour_keeps_the_time(con):
    hours = minutes_by(con, "hour")

    assert (hours[3].start, hours[3].minutes) == (datetime(2024, 2, 1, 21), 1.0)


def test_minutes_by_respects_the_window(con):
    assert minutes_by(con, "month", window=year(2023)) == []


def test_listening_clock_has_every_weekday_and_hour(con):
    clock = listening_clock(con)

    assert len(clock) == 7 * 24
    assert sum(c.minutes for c in clock if c.hour == 9) == 6.0  # six 9am plays across the week
    thursday_9pm = next(c for c in clock if (c.weekday, c.hour) == (3, 21))
    assert thursday_9pm.minutes == 1.0


def test_longest_and_current_streak(con):
    s = streaks(con, today=date(2024, 2, 12))

    assert (s.longest.days, s.longest.start, s.longest.end) == (
        4,
        date(2024, 1, 30),
        date(2024, 2, 2),
    )
    assert (s.current.days, s.current.start) == (2, date(2024, 2, 10))


def test_streak_is_broken_after_a_day_without_listening(con):
    assert streaks(con, today=date(2024, 2, 13)).current.days == 0


def test_skips_under_30_seconds_do_not_keep_a_streak_alive(tmp_path):
    con = connect_rows(tmp_path, ["2024-02-01T09:00:00Z"], ms_played=5_000)

    assert streaks(con, today=date(2024, 2, 1)).longest.days == 0
