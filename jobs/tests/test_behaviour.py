import json
from datetime import UTC, date, datetime

import pytest

from stats_jobs.behaviour import (
    discoveries,
    most_skipped,
    new_artists_by_month,
    on_repeat,
    skip_rate,
)
from stats_jobs.stats import connect
from stats_jobs.windows import Window

N = iter(range(1000))


def listen(artist, played_at, ms_played=200_000, track="Song", skipped=False):
    return {
        "listen_id": f"l{next(N)}",
        "user_id": "u1",
        "played_at": played_at,
        "track_id": f"{artist}-{track}",
        "track_name": track,
        "artist_name": artist,
        "album_name": "Album",
        "source": "export",
        "ms_played": ms_played,
        "skipped": skipped,
    }


@pytest.fixture
def con(tmp_path):
    rows = [
        listen("Old", "2023-05-01T10:00:00Z"),
        listen("Old", "2024-02-01T10:00:00Z", ms_played=5_000),
        # Spotify's skipped flag is ignored; only the 30-second rule counts.
        listen("Old", "2024-02-02T10:00:00Z", ms_played=4_000, skipped=False),
        listen("New", "2024-02-10T10:00:00Z", skipped=True),
        listen("New", "2024-02-10T11:00:00Z", track="Banger"),
        listen("New", "2024-02-10T12:00:00Z", track="Banger"),
        listen("New", "2024-02-10T13:00:00Z", track="Banger"),
        listen("Newer", "2024-03-05T10:00:00Z", ms_played=1_000),
        listen("Newer", "2024-03-06T10:00:00Z"),
    ]
    path = tmp_path / "listens.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in rows))
    return connect(path)


FEB_2024 = Window(
    "feb_2024", start=datetime(2024, 2, 1, tzinfo=UTC), end=datetime(2024, 3, 1, tzinfo=UTC)
)


def test_skip_rate_counts_plays_under_30_seconds(con):
    assert skip_rate(con) == pytest.approx(3 / 9)
    assert skip_rate(con, FEB_2024) == pytest.approx(2 / 6)


def test_most_skipped_needs_enough_plays(con):
    rows = most_skipped(con, "artist", min_plays=3)

    assert [(r.name, r.plays, round(r.skip_rate, 2)) for r in rows] == [
        ("Old", 3, 0.67),
        ("New", 4, 0.0),
    ]


def test_discoveries_are_artists_first_streamed_in_the_window(con):
    assert [(d.artist_name, d.first_played, d.streams) for d in discoveries(con, FEB_2024)] == [
        ("New", date(2024, 2, 10), 4)
    ]


def test_first_stream_ignores_skips(con):
    # Newer's first play (5 March) was a 1-second skip; the first stream was on 6 March.
    newer = next(d for d in discoveries(con) if d.artist_name == "Newer")

    assert newer.first_played == date(2024, 3, 6)


def test_new_artists_by_month(con):
    assert new_artists_by_month(con) == [
        (date(2023, 5, 1), 1),
        (date(2024, 2, 1), 1),
        (date(2024, 3, 1), 1),
    ]


def test_on_repeat_finds_the_most_streams_of_a_track_in_one_day(con):
    [top] = on_repeat(con, limit=1)

    assert (top.track_name, top.artist_name, top.day, top.streams) == (
        "Banger",
        "New",
        date(2024, 2, 10),
        3,
    )
