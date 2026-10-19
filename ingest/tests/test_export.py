import json
import zipfile
from datetime import UTC, datetime

import pytest

from stats_ingest.export import parse_export, parse_records
from stats_ingest.listen import track_id_from_uri


def play(**overrides):
    """A made-up export record shaped like Spotify's Extended Streaming History."""
    record = {
        "ts": "2024-03-01T12:00:00Z",
        "platform": "ios",
        "ms_played": 200_000,
        "conn_country": "GB",
        "ip_addr": "203.0.113.7",
        "master_metadata_track_name": "Test Song",
        "master_metadata_album_artist_name": "Test Artist",
        "master_metadata_album_album_name": "Test Album",
        "spotify_track_uri": "spotify:track:abc123",
        "episode_name": None,
        "episode_show_name": None,
        "spotify_episode_uri": None,
        "audiobook_title": None,
        "audiobook_uri": None,
        "audiobook_chapter_uri": None,
        "audiobook_chapter_title": None,
        "reason_start": "trackdone",
        "reason_end": "trackdone",
        "shuffle": False,
        "skipped": False,
        "offline": False,
        "offline_timestamp": 1709294200,
        "incognito_mode": False,
    }
    return record | overrides


def test_track_play_becomes_a_listen():
    [listen] = parse_records([play()], user_id="u1").listens

    assert listen.user_id == "u1"
    assert listen.played_at == datetime(2024, 3, 1, 12, 0, tzinfo=UTC)
    assert listen.track_id == "abc123"
    assert (listen.track_name, listen.artist_name, listen.album_name) == (
        "Test Song",
        "Test Artist",
        "Test Album",
    )
    assert listen.ms_played == 200_000
    assert listen.source == "export"


def test_personal_network_fields_are_not_kept():
    [listen] = parse_records([play()], user_id="u1").listens
    row = listen.to_dict()

    assert "ip_addr" not in row
    assert "conn_country" not in row
    assert "203.0.113.7" not in json.dumps(row)


def test_podcasts_and_rows_without_metadata_are_skipped():
    episode = play(
        spotify_track_uri=None,
        master_metadata_track_name=None,
        spotify_episode_uri="spotify:episode:xyz",
    )
    unknown = play(spotify_track_uri=None, master_metadata_track_name=None)

    result = parse_records([episode, unknown, play()], user_id="u1")

    assert len(result.listens) == 1
    assert result.skipped == {"podcast_episode": 1, "no_track_metadata": 1}


def test_quick_skips_in_the_same_second_are_separate_listens():
    first = play(ms_played=1_200, reason_end="fwdbtn", offline_timestamp=1709294199)
    second = play(ms_played=800, reason_end="fwdbtn", offline_timestamp=1709294200)

    assert len(parse_records([first, second], user_id="u1").listens) == 2


def test_exact_duplicate_records_are_dropped():
    result = parse_records([play(), play()], user_id="u1")

    assert len(result.listens) == 1
    assert result.skipped == {"duplicate": 1}


def test_listen_id_is_stable_and_scoped_to_the_user():
    a = parse_records([play()], user_id="u1").listens[0]
    again = parse_records([play()], user_id="u1").listens[0]
    other_user = parse_records([play()], user_id="u2").listens[0]

    assert a.listen_id == again.listen_id
    assert a.listen_id != other_user.listen_id


def test_reads_an_unzipped_export_folder_and_ignores_other_files(tmp_path):
    folder = tmp_path / "Spotify Extended Streaming History"
    folder.mkdir()
    (folder / "Streaming_History_Audio_2024.json").write_text(json.dumps([play()]))
    (folder / "Streaming_History_Video_2024.json").write_text(
        json.dumps([play(ts="2024-03-02T09:00:00Z")])
    )
    (folder / "Userdata.json").write_text(json.dumps({"username": "x"}))

    assert len(parse_export(tmp_path, user_id="u1").listens) == 2


def test_reads_the_export_zip_directly(tmp_path):
    archive = tmp_path / "my_spotify_data.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr(
            "Spotify Extended Streaming History/Streaming_History_Audio_2024.json",
            json.dumps([play()]),
        )

    assert len(parse_export(archive, user_id="u1").listens) == 1


def test_missing_export_path_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        parse_export(tmp_path / "nope.zip", user_id="u1")


@pytest.mark.parametrize("uri", ["spotify:episode:abc", "spotify:track:", "nonsense"])
def test_track_id_rejects_non_track_uris(uri):
    with pytest.raises(ValueError):
        track_id_from_uri(uri)
