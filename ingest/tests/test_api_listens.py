from datetime import UTC, datetime

from stats_ingest.api_listens import listen_from_api


def item(played_at="2026-10-22T09:15:31.123Z"):
    return {
        "played_at": played_at,
        "track": {
            "id": "abc123",
            "name": "Test Song",
            "duration_ms": 180_000,
            "artists": [{"name": "Main Artist"}, {"name": "Feature"}],
            "album": {"name": "Test Album"},
        },
        "context": None,
    }


def test_api_item_becomes_a_listen():
    listen = listen_from_api(item(), user_id="u1")

    assert listen.played_at == datetime(2026, 10, 22, 9, 15, 31, 123_000, tzinfo=UTC)
    assert (listen.track_id, listen.track_name) == ("abc123", "Test Song")
    assert (listen.artist_name, listen.album_name) == ("Main Artist", "Test Album")
    assert listen.source == "api"
    assert (listen.ms_played, listen.skipped, listen.track_duration_ms) == (None, None, 180_000)


def test_timestamps_without_milliseconds_parse():
    assert listen_from_api(item("2026-10-22T09:15:31Z"), "u1").played_at.microsecond == 0


def test_the_same_api_play_always_gets_the_same_id():
    assert listen_from_api(item(), "u1").listen_id == listen_from_api(item(), "u1").listen_id
    assert listen_from_api(item(), "u1").listen_id != listen_from_api(item(), "u2").listen_id
