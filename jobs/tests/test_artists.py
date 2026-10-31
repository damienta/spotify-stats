import json
from datetime import UTC, datetime

import pytest

from stats_ingest.storage import artist_stat_name
from stats_jobs.artists import PAGES_FROM_EACH, TOP_TRACKS, artist_pages, page_artists
from stats_jobs.catalog import Catalog, enrich
from stats_jobs.documents import build_documents
from stats_jobs.stats import TopRow, connect

NOW = datetime(2026, 10, 1, tzinfo=UTC)


def listen(n, artist, track, played_at, ms_played=60_000):
    return {
        "listen_id": f"l{n}",
        "user_id": "u1",
        "played_at": played_at,
        "track_id": f"{artist}-{track}",
        "track_name": track,
        "artist_name": artist,
        "album_name": "Album",
        "source": "export",
        "ms_played": ms_played,
    }


@pytest.fixture
def con(tmp_path):
    rows = [
        listen(1, "A", "First", "2025-01-05T10:00:00Z"),
        listen(2, "A", "Hit", "2025-01-20T10:00:00Z"),
        listen(3, "A", "Hit", "2025-03-02T10:00:00Z"),
        listen(4, "A", "Skipped", "2025-03-03T10:00:00Z", ms_played=5_000),
        listen(5, "B", "Other", "2026-09-28T10:00:00Z", ms_played=120_000),
    ]
    path = tmp_path / "listens.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in rows))
    return connect(path)


def test_an_artist_page_sums_up_their_listening(con):
    docs = build_documents(con, "u1", NOW)
    page = docs[artist_stat_name("A")]["data"]

    assert page["name"] == "A"
    assert page["minutes"] == pytest.approx(185_000 / 60_000, abs=1e-4)
    assert (page["streams"], page["tracks"]) == (3, 3)
    assert page["share"] == pytest.approx(185 / 305, abs=1e-4)
    assert page["first_played"].startswith("2025-01-05")
    assert page["first_track"] == "First"
    assert page["last_played"].startswith("2025-03-03")
    # Top all time, but not played at all in the last 12 months.
    assert page["ranks"] == {"4_weeks": None, "6_months": None, "12_months": None, "all_time": 1}
    assert docs[artist_stat_name("B")]["data"]["ranks"]["4_weeks"] == 1
    assert [(m["start"], m["minutes"]) for m in page["minutes_by_month"]] == [
        ("2025-01-01", 2.0),
        ("2025-03-01", pytest.approx(65_000 / 60_000, abs=1e-4)),
    ]
    assert [t["name"] for t in page["top_tracks"]] == ["Hit", "First", "Skipped"]
    assert page["top_tracks"][0]["artist_name"] == "A"
    assert page["track_id"].startswith("A-")


def test_pages_are_for_the_top_artists_of_every_range_once_each():
    def rows(*names):
        return [TopRow(n, None, 1, 1.0) for n in names]

    many = [f"Artist {n}" for n in range(PAGES_FROM_EACH + 10)]
    stats = {
        "top_artists#4_weeks": rows("New", "Both"),
        "top_artists#all_time": rows("Both", *many),
    }

    names = page_artists(stats)

    assert names[:2] == ["New", "Both"]
    assert len(names) == 2 + PAGES_FROM_EACH - 1
    assert many[PAGES_FROM_EACH - 1] not in names


def test_top_tracks_stop_at_the_limit(tmp_path):
    rows = [
        listen(n, "A", f"Song {n}", f"2025-01-{1 + n:02d}T10:00:00Z", ms_played=60_000 + n)
        for n in range(TOP_TRACKS + 5)
    ]
    path = tmp_path / "listens.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in rows))
    con = connect(path)
    stats = build_documents(con, "u1", NOW)
    page = stats[artist_stat_name("A")]["data"]

    assert len(page["top_tracks"]) == TOP_TRACKS
    assert page["top_tracks"][0]["name"] == f"Song {TOP_TRACKS + 4}"


def test_no_listens_no_pages(con):
    assert artist_pages(con, {}) == {}


def test_artist_pages_get_the_artists_picture_and_song_covers(con):
    def fetch(path):
        if path.startswith("/tracks/"):
            return {
                "external_urls": {"spotify": f"https://open.spotify.com{path}"},
                "album": {"images": [{"url": "https://i.scdn.co/cover", "width": 300}]},
                "artists": [{"id": "a", "name": "A"}],
            }
        return {"external_urls": {"spotify": "https://open.spotify.com/artist/a"}, "images": []}

    docs = build_documents(con, "u1", NOW)
    enrich(docs, Catalog(fetch))
    page = docs[artist_stat_name("A")]["data"]

    assert page["url"] == "https://open.spotify.com/artist/a"
    assert page["top_tracks"][0]["image"] == "https://i.scdn.co/cover"
