import threading

import httpx
import pytest

from stats_ingest.spotify import SpotifyError, Tokens
from stats_ingest.spotify_cli import load_tokens, save_tokens, wait_for_callback


def test_tokens_round_trip_through_the_token_file(tmp_path):
    path = tmp_path / "data" / "spotify_token.json"
    tokens = Tokens("a", "r", 123.0)

    save_tokens(path, tokens)

    assert load_tokens(path) == tokens


def test_missing_token_file_says_to_log_in(tmp_path):
    with pytest.raises(SpotifyError, match="spotify-login"):
        load_tokens(tmp_path / "nope.json")


def test_callback_server_returns_the_query_spotify_sends(unused_port):
    redirect = f"http://127.0.0.1:{unused_port}/callback"
    result = {}
    thread = threading.Thread(target=lambda: result.update(wait_for_callback(redirect, 10)))
    thread.start()

    for _ in range(50):
        try:
            response = httpx.get(f"{redirect}?code=abc&state=xyz", timeout=1)
            break
        except httpx.ConnectError:
            threading.Event().wait(0.05)
    thread.join(timeout=5)

    assert response.status_code == 200
    assert result == {"code": "abc", "state": "xyz"}


@pytest.fixture
def unused_port():
    import socket

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]
