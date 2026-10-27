from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from stats_ingest.spotify import (
    SpotifyClient,
    SpotifyConfig,
    SpotifyError,
    Tokens,
    app_token,
    authorize_url,
    exchange_code,
    refresh_tokens,
)

CONFIG = SpotifyConfig("client-id", "client-secret", "http://127.0.0.1:8000/callback")
FRESH = Tokens("access-1", "refresh-1", expires_at=10_000)


def fake_spotify(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_authorize_url_asks_only_for_listening_activity():
    query = parse_qs(urlparse(authorize_url(CONFIG, state="xyz")).query)

    assert query["client_id"] == ["client-id"]
    assert query["redirect_uri"] == ["http://127.0.0.1:8000/callback"]
    assert query["scope"] == ["user-read-recently-played user-read-currently-playing"]
    assert query["state"] == ["xyz"]


def test_exchange_code_returns_tokens_with_an_expiry():
    def handler(request):
        assert request.headers["Authorization"].startswith("Basic ")
        assert b"grant_type=authorization_code" in request.content
        return httpx.Response(
            200, json={"access_token": "a", "refresh_token": "r", "expires_in": 3600}
        )

    tokens = exchange_code(fake_spotify(handler), CONFIG, "code", now=1_000)

    assert tokens == Tokens("a", "r", 4_600)


def test_refresh_keeps_the_old_refresh_token_when_spotify_sends_none():
    def handler(request):
        return httpx.Response(200, json={"access_token": "a2", "expires_in": 3600})

    tokens = refresh_tokens(fake_spotify(handler), CONFIG, FRESH, now=0)

    assert (tokens.access_token, tokens.refresh_token) == ("a2", "refresh-1")


def test_failed_token_request_raises():
    def handler(request):
        return httpx.Response(400, json={"error": "invalid_grant"})

    with pytest.raises(SpotifyError, match="400"):
        exchange_code(fake_spotify(handler), CONFIG, "bad-code")


def play(played_at):
    return {"played_at": played_at, "track": {"id": "t"}}


def test_recently_played_follows_pages_and_returns_oldest_first():
    def handler(request):
        if "page2" in str(request.url):
            return httpx.Response(200, json={"items": [play("2026-10-22T08:00:00Z")]})
        assert request.url.params["after"] == "123"
        return httpx.Response(
            200,
            json={
                "items": [play("2026-10-22T10:00:00Z"), play("2026-10-22T09:00:00Z")],
                "next": "https://api.spotify.com/v1/me/player/recently-played?page2",
            },
        )

    client = SpotifyClient(fake_spotify(handler), CONFIG, FRESH, clock=lambda: 0)

    items = client.recently_played(after_ms=123)

    assert [i["played_at"][11:13] for i in items] == ["08", "09", "10"]


def test_waits_for_retry_after_when_rate_limited():
    calls, slept = [], []

    def handler(request):
        calls.append(1)
        if len(calls) == 1:
            return httpx.Response(429, headers={"Retry-After": "2"})
        return httpx.Response(200, json={"id": "me"})

    client = SpotifyClient(
        fake_spotify(handler), CONFIG, FRESH, clock=lambda: 0, sleep=slept.append
    )

    assert client.me() == {"id": "me"}
    assert slept == [2.0]


def test_gives_up_after_repeated_rate_limits():
    def handler(request):
        return httpx.Response(429, headers={"Retry-After": "0"})

    client = SpotifyClient(
        fake_spotify(handler), CONFIG, FRESH, clock=lambda: 0, sleep=lambda s: None
    )

    with pytest.raises(SpotifyError, match="rate limited"):
        client.me()


def test_refreshes_an_expired_token_before_calling_and_reports_it():
    seen_auth, saved = [], []

    def handler(request):
        if request.url.host == "accounts.spotify.com":
            return httpx.Response(200, json={"access_token": "access-2", "expires_in": 3600})
        seen_auth.append(request.headers["Authorization"])
        return httpx.Response(200, json={"id": "me"})

    client = SpotifyClient(
        fake_spotify(handler), CONFIG, FRESH, on_refresh=saved.append, clock=lambda: 9_999
    )
    client.me()

    assert seen_auth == ["Bearer access-2"]
    assert saved[0].access_token == "access-2"


def test_refreshes_once_when_spotify_rejects_the_token():
    def handler(request):
        if request.url.host == "accounts.spotify.com":
            return httpx.Response(200, json={"access_token": "access-2", "expires_in": 3600})
        if request.headers["Authorization"] == "Bearer access-1":
            return httpx.Response(401)
        return httpx.Response(200, json={"id": "me"})

    client = SpotifyClient(fake_spotify(handler), CONFIG, FRESH, clock=lambda: 0)

    assert client.me() == {"id": "me"}


def test_currently_playing_is_none_when_nothing_plays():
    def handler(request):
        return httpx.Response(204)

    assert (
        SpotifyClient(fake_spotify(handler), CONFIG, FRESH, clock=lambda: 0).currently_playing()
        is None
    )


def test_errors_carry_the_status():
    def handler(request):
        return httpx.Response(403, json={"error": "insufficient scope"})

    with pytest.raises(SpotifyError) as e:
        SpotifyClient(fake_spotify(handler), CONFIG, FRESH, clock=lambda: 0).currently_playing()
    assert e.value.status == 403


def test_app_token_uses_client_credentials():
    def handler(request):
        assert b"grant_type=client_credentials" in request.content
        return httpx.Response(200, json={"access_token": "app", "expires_in": 3600})

    tokens = app_token(fake_spotify(handler), CONFIG, now=0)

    assert (tokens.access_token, tokens.expires_at) == ("app", 3600)
