import json

import pytest

from stats_jobs.stats import connect, top


def listen(n, track_id, track, artist, album, ms_played=200_000):
    return {
        "listen_id": f"l{n}",
        "user_id": "u1",
        "played_at": f"2024-03-01T12:{n:02d}:00Z",
        "track_id": track_id,
        "track_name": track,
        "artist_name": artist,
        "album_name": album,
        "source": "export",
        "ms_played": ms_played,
    }


@pytest.fixture
def con(tmp_path):
    rows = [
        # The same song released as a single and on an album: two track IDs, one track.
        listen(1, "single", "Hit", "A", "Hit (Single)"),
        listen(2, "album", "Hit", "A", "Big Album"),
        listen(3, "album", "Hit", "A", "Big Album"),
        listen(4, "t2", "Deep Cut", "A", "Big Album"),
        # Two artists with a song of the same name stay apart.
        listen(5, "t3", "Intro", "B", "Debut"),
        listen(6, "t4", "Intro", "C", "Debut"),
        listen(7, "t4", "Intro", "C", "Debut", ms_played=10_000),
    ]
    path = tmp_path / "listens.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in rows))
    return connect(path)


def test_top_tracks_merge_releases_of_the_same_song(con):
    rows = top(con, "track", limit=10)

    assert [(r.name, r.artist_name, r.streams) for r in rows] == [
        ("Hit", "A", 3),
        ("Intro", "C", 1),  # ties on streams go to more time played (its 10 s skip)
        ("Deep Cut", "A", 1),
        ("Intro", "B", 1),
    ]


def test_top_albums_are_per_artist(con):
    rows = top(con, "album", limit=10)

    assert [(r.name, r.artist_name, r.streams) for r in rows] == [
        ("Big Album", "A", 3),
        ("Debut", "C", 1),
        ("Debut", "B", 1),
        ("Hit (Single)", "A", 1),
    ]


def test_top_artists_have_no_artist_column(con):
    [first] = top(con, "artist", limit=1)

    assert (first.name, first.artist_name, first.streams) == ("A", None, 4)
