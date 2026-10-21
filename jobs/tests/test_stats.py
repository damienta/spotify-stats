import json

import pytest

from stats_jobs.stats import connect, top, totals, write_parquet


def listen(artist, ms_played, track_id="t1", played_at="2024-03-01T12:00:00Z"):
    return {
        "listen_id": f"{artist}-{ms_played}-{played_at}",
        "user_id": "u1",
        "played_at": played_at,
        "track_id": track_id,
        "track_name": "Song",
        "artist_name": artist,
        "album_name": "Album",
        "source": "export",
        "ms_played": ms_played,
    }


@pytest.fixture
def con(tmp_path):
    rows = [
        listen("A", 200_000, played_at="2024-01-01T08:00:00Z"),
        listen("A", 200_000, track_id="t2"),
        listen("A", 5_000),  # skipped after 5s: counts towards hours, not streams
        listen("B", 3_600_000, track_id="t3", played_at="2024-06-30T22:00:00Z"),
        listen("C", 29_999, track_id="t4"),
    ]
    path = tmp_path / "listens.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in rows))
    return connect(path)


def test_totals(con):
    t = totals(con)

    assert t.streams == 3
    assert t.hours == pytest.approx((400_000 + 5_000 + 3_600_000 + 29_999) / 3_600_000)
    assert (t.artists, t.tracks) == (3, 4)
    assert t.first_played.startswith("2024-01-01")
    assert t.last_played.startswith("2024-06-30")


def test_top_artists_rank_by_streams_over_30_seconds(con):
    ranked = top(con, "artist", limit=3)

    assert [(a.name, a.streams) for a in ranked] == [("A", 2), ("B", 1), ("C", 0)]
    assert ranked[1].hours == pytest.approx(1.0)


def test_top_artists_respects_the_limit(con):
    assert len(top(con, "artist", limit=1)) == 1


def test_duplicate_listen_ids_are_counted_once(tmp_path):
    play = listen("A", 200_000)
    path = tmp_path / "listens.jsonl"
    path.write_text("\n".join(json.dumps(play) for _ in range(3)))

    assert totals(connect(path)).streams == 1


def test_export_row_wins_over_api_row_with_the_same_id(tmp_path):
    api = listen("A", 200_000) | {"source": "api", "ms_played": None}
    export = listen("A", 200_000)
    path = tmp_path / "listens.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in (api, export)))

    assert connect(path).execute("SELECT source, ms_played FROM listens").fetchall() == [
        ("export", 200_000)
    ]


def test_parquet_round_trip_keeps_every_listen(con, tmp_path):
    dest = tmp_path / "listens.parquet"

    assert write_parquet(con, dest) == 5
    assert totals(connect(dest)) == totals(con)
