import json
from datetime import UTC, datetime

import pytest

from stats_jobs.stats import connect, top_artists, totals
from stats_jobs.windows import ALL_TIME, by_name, standard_windows, year

NOW = datetime(2026, 10, 1, tzinfo=UTC)


def listen(artist, played_at, ms_played=200_000):
    return {
        "listen_id": f"{artist}-{played_at}",
        "user_id": "u1",
        "played_at": played_at,
        "track_id": artist,
        "track_name": "Song",
        "artist_name": artist,
        "album_name": "Album",
        "source": "export",
        "ms_played": ms_played,
    }


@pytest.fixture
def con(tmp_path):
    rows = [
        listen("old", "2020-05-01T10:00:00Z"),
        listen("last_year", "2025-12-31T23:30:00Z"),
        listen("recent", "2026-09-20T10:00:00Z"),
        listen("recent", "2026-09-25T10:00:00Z"),
        listen("summer", "2026-06-30T23:30:00Z"),  # 00:30 on 1 July in London (BST)
    ]
    path = tmp_path / "listens.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in rows))
    return connect(path)


def test_rolling_windows_only_count_recent_plays(con):
    four_weeks, six_months, twelve_months, all_time = standard_windows(NOW)

    assert totals(con, four_weeks).streams == 2
    assert totals(con, six_months).streams == 3
    assert totals(con, twelve_months).streams == 4
    assert totals(con, all_time).streams == 5


def test_top_artists_within_a_window(con):
    [top] = top_artists(con, limit=1, window=by_name("4_weeks", NOW))

    assert (top.artist_name, top.streams) == ("recent", 2)


def test_year_window_uses_the_london_calendar(con):
    assert totals(con, year(2025)).streams == 1
    assert totals(con, year(2026)).streams == 3


def test_local_time_follows_british_summer_time(con):
    [(local,)] = con.execute(
        "SELECT played_at_local FROM listens WHERE artist_name = 'summer'"
    ).fetchall()

    assert local == datetime(2026, 7, 1, 0, 30)


def test_empty_window_has_zero_totals(con):
    t = totals(con, year(2019))

    assert (t.streams, t.hours, t.first_played) == (0, 0, "")


def test_window_names():
    assert by_name("all_time", NOW) == ALL_TIME
    assert by_name("year_2024", NOW).name == "year_2024"
    with pytest.raises(ValueError):
        by_name("fortnight", NOW)
