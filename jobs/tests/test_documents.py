import json
from datetime import UTC, datetime

import pytest

from stats_jobs.documents import MAX_DOCUMENT_BYTES, build_documents, wrapped
from stats_jobs.stats import connect

NOW = datetime(2026, 10, 1, tzinfo=UTC)


def listen(n, artist, played_at, ms_played=200_000):
    return {
        "listen_id": f"l{n}",
        "user_id": "u1",
        "played_at": played_at,
        "track_id": f"t{n % 3}",
        "track_name": f"Song {n % 3}",
        "artist_name": artist,
        "album_name": "Album",
        "source": "export",
        "ms_played": ms_played,
    }


@pytest.fixture
def con(tmp_path):
    rows = [
        listen(n, "A" if n % 2 else "B", f"2025-0{1 + n % 9}-1{n % 10}T10:00:00Z")
        for n in range(40)
    ]
    rows.append(listen(99, "C", "2026-09-28T10:00:00Z"))
    path = tmp_path / "listens.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in rows))
    return connect(path)


def test_documents_cover_every_window_year_and_stat(con):
    docs = build_documents(con, "u1", NOW)

    for window in ("4_weeks", "6_months", "12_months", "all_time", "year_2025", "year_2026"):
        assert f"totals#{window}" in docs
        assert f"top_tracks#{window}" in docs
        assert f"listening_clock#{window}" in docs
    for window in ("today", "this_week", "this_month", "this_year"):
        assert f"totals#{window}" in docs
    assert "minutes_by_hour#today" in docs
    assert "minutes_by_day#this_month" in docs
    assert "minutes_by_day#4_weeks" in docs
    assert "minutes_by_month#all_time" in docs
    assert {"streaks", "wrapped#2025", "wrapped#2026"} <= docs.keys()


def test_documents_are_json_with_their_key_and_owner(con):
    docs = build_documents(con, "u1", NOW)

    doc = docs["top_artists#all_time"]
    assert (doc["user_id"], doc["stat_name"]) == ("u1", "top_artists#all_time")
    assert doc["data"][0] == {
        "name": "A",
        "artist_name": None,
        "streams": 20,
        "hours": 1.1111,
        "track_id": "t0",
    }
    assert docs["totals#4_weeks"]["data"]["streams"] == 1
    for d in docs.values():
        assert len(json.dumps(d).encode()) < MAX_DOCUMENT_BYTES


def test_wrapped_summarises_one_year(con):
    w = wrapped(con, 2025)

    assert w["minutes"] == round(40 * 200_000 / 60_000)
    assert [a.name for a in w["top_artists"]] == ["A", "B"]
    assert w["top_month"].start.year == 2025


def test_materialized_listens_give_the_same_documents(con, tmp_path):
    path = tmp_path / "listens.parquet"
    con.sql("SELECT * EXCLUDE (played_at_local) FROM listens").write_parquet(str(path))

    assert build_documents(connect(path, materialize=True), "u1", NOW) == build_documents(
        connect(path), "u1", NOW
    )
