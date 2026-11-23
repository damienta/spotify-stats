import json
from datetime import UTC, datetime

import pytest

from stats_ingest.storage import album_stat_name, artist_stat_name
from stats_jobs.albums import TOP_TRACKS, album_pages, page_albums
from stats_jobs.artists import PAGES_FROM_EACH, TOP_ALBUMS
from stats_jobs.catalog import Catalog, enrich
from stats_jobs.documents import build_documents
from stats_jobs.stats import TopRow, connect

NOW = datetime(2026, 10, 1, tzinfo=UTC)


def listen(n, album, track, played_at, artist="A", ms_played=60_000):
    return {
        "listen_id": f"l{n}",
        "user_id": "u1",
        "played_at": played_at,
        "track_id": f"{album}-{track}",
        "track_name": track,
        "artist_name": artist,
        "album_name": album,
        "source": "export",
        "ms_played": ms_played,
    }


def connect_rows(tmp_path, rows):
    path = tmp_path / "listens.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in rows))
    return connect(path)


@pytest.fixture
def con(tmp_path):
    # London is UTC+1 in summer, so 23:30 UTC on 1 June is 00:30 on 2 June: Night.
    return connect_rows(
        tmp_path,
        [
            listen(1, "Debut", "Opener", "2025-06-01T08:00:00Z"),
            listen(2, "Debut", "Single", "2025-06-01T09:00:00Z"),
            listen(3, "Debut", "Single", "2025-06-01T23:30:00Z"),
            listen(4, "Debut", "Single", "2025-07-10T15:00:00Z", ms_played=180_000),
            listen(5, "Debut", "Skipped", "2025-07-11T15:00:00Z", ms_played=5_000),
            listen(6, "Second", "Other", "2026-09-28T10:00:00Z", ms_played=120_000),
            # Same album name, different artist: a different album.
            listen(7, "Debut", "Theirs", "2026-09-29T10:00:00Z", artist="B"),
        ],
    )


def test_an_album_page_sums_up_its_listening(con):
    docs = build_documents(con, "u1", NOW)
    page = docs[album_stat_name("Debut", "A")]["data"]

    assert (page["name"], page["artist_name"]) == ("Debut", "A")
    assert page["minutes"] == pytest.approx(365_000 / 60_000, abs=1e-4)
    assert (page["streams"], page["tracks"]) == (4, 3)
    assert page["first_played"].startswith("2025-06-01")
    assert page["first_track"] == "Opener"
    assert page["last_played"].startswith("2025-07-11")
    assert page["ranks"]["all_time"] == 1
    assert page["ranks"]["4_weeks"] is None
    assert [t["name"] for t in page["top_tracks"]] == ["Single", "Opener", "Skipped"]
    assert page["track_id"].startswith("Debut-")
    # Three plays on 1-2 June London time; 10 July had the single long play.
    assert page["biggest_day"] == {"start": "2025-07-10", "minutes": 3.0}
    assert page["time_of_day"] == {
        "Night": 1.0,
        "Morning": 2.0,
        "Afternoon": pytest.approx(185_000 / 60_000, abs=1e-4),
        "Evening": 0.0,
    }


def test_albums_with_the_same_name_by_different_artists_are_different_pages(con):
    docs = build_documents(con, "u1", NOW)

    theirs = docs[album_stat_name("Debut", "B")]["data"]
    assert [t["name"] for t in theirs["top_tracks"]] == ["Theirs"]
    assert album_stat_name("Debut", "a") == album_stat_name("debut", "A")


def test_pages_are_for_the_top_albums_of_every_range_once_each():
    def rows(*names):
        return [TopRow(n, "A", 1, 1.0) for n in names]

    many = [f"Album {n}" for n in range(PAGES_FROM_EACH + 10)]
    stats = {
        "top_albums#4_weeks": rows("New", "Both"),
        "top_albums#all_time": rows("Both", *many),
    }

    keys = page_albums(stats)

    assert keys[:2] == [("New", "A"), ("Both", "A")]
    assert len(keys) == 2 + PAGES_FROM_EACH - 1


def test_every_song_played_is_listed_up_to_the_limit(tmp_path):
    con = connect_rows(
        tmp_path,
        [
            listen(
                n, "Long", f"Song {n}", f"2025-01-{1 + n % 28:02d}T10:00:00Z", ms_played=60_000 + n
            )
            for n in range(TOP_TRACKS + 5)
        ],
    )
    page = build_documents(con, "u1", NOW)[album_stat_name("Long", "A")]["data"]

    assert len(page["top_tracks"]) == TOP_TRACKS
    assert page["top_tracks"][0]["name"] == f"Song {TOP_TRACKS + 4}"


def test_no_listens_no_pages(con):
    assert album_pages(con, {}) == {}


def test_artist_pages_list_their_albums_and_which_have_a_page(con):
    docs = build_documents(con, "u1", NOW)
    albums = docs[artist_stat_name("A")]["data"]["top_albums"]

    assert [(a["name"], a["page"]) for a in albums] == [("Debut", True), ("Second", True)]
    assert len(albums) <= TOP_ALBUMS


def test_album_pages_get_the_cover_and_link(con):
    def fetch(path):
        return {
            "external_urls": {"spotify": f"https://open.spotify.com{path}"},
            "album": {
                "images": [{"url": "https://i.scdn.co/cover", "width": 300}],
                "external_urls": {"spotify": "https://open.spotify.com/album/x"},
            },
            "artists": [{"id": "a", "name": "A"}],
        }

    docs = build_documents(con, "u1", NOW)
    enrich(docs, Catalog(fetch))
    page = docs[album_stat_name("Debut", "A")]["data"]

    assert page["image"] == "https://i.scdn.co/cover"
    assert page["url"] == "https://open.spotify.com/album/x"
    assert page["top_tracks"][0]["image"] == "https://i.scdn.co/cover"
    assert (
        docs[artist_stat_name("A")]["data"]["top_albums"][0]["image"] == "https://i.scdn.co/cover"
    )
