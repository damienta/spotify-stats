"""A small Spotify Web API client: OAuth tokens and recently played tracks.

Uses the Authorization Code flow. Only the `user-read-recently-played` scope is requested,
so the app can read what someone played and nothing else.
"""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import Any
from urllib.parse import urlencode

import httpx

AUTHORIZE_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
API_URL = "https://api.spotify.com/v1"
SCOPES = ("user-read-recently-played",)

# Refresh a little early so a token never expires mid-request.
EXPIRY_MARGIN_S = 60
MAX_RETRIES = 3


class SpotifyError(Exception):
    pass


@dataclass(frozen=True)
class SpotifyConfig:
    client_id: str
    client_secret: str
    redirect_uri: str

    @classmethod
    def from_env(cls) -> SpotifyConfig:
        try:
            return cls(
                client_id=os.environ["SPOTIFY_CLIENT_ID"],
                client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
                redirect_uri=os.environ["SPOTIFY_REDIRECT_URI"],
            )
        except KeyError as e:
            raise SpotifyError(f"{e.args[0]} is not set (see .env.example)") from None


@dataclass(frozen=True)
class Tokens:
    access_token: str
    refresh_token: str
    expires_at: float  # Unix time

    def expired(self, now: float) -> bool:
        return now >= self.expires_at - EXPIRY_MARGIN_S

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def authorize_url(config: SpotifyConfig, state: str) -> str:
    """Where to send the user to approve the app. `state` guards against forged callbacks."""
    query = {
        "client_id": config.client_id,
        "response_type": "code",
        "redirect_uri": config.redirect_uri,
        "scope": " ".join(SCOPES),
        "state": state,
    }
    return f"{AUTHORIZE_URL}?{urlencode(query)}"


def _token_request(
    http: httpx.Client, config: SpotifyConfig, form: dict[str, str], now: float
) -> dict[str, Any]:
    response = http.post(TOKEN_URL, data=form, auth=(config.client_id, config.client_secret))
    if response.status_code != 200:
        raise SpotifyError(f"token request failed: {response.status_code} {response.text}")
    body = response.json()
    body["expires_at"] = now + body["expires_in"]
    return body


def exchange_code(
    http: httpx.Client, config: SpotifyConfig, code: str, now: float | None = None
) -> Tokens:
    """Swap the one-time code from the login redirect for access and refresh tokens."""
    form = {"grant_type": "authorization_code", "code": code, "redirect_uri": config.redirect_uri}
    body = _token_request(http, config, form, time.time() if now is None else now)
    return Tokens(body["access_token"], body["refresh_token"], body["expires_at"])


def refresh_tokens(
    http: httpx.Client, config: SpotifyConfig, tokens: Tokens, now: float | None = None
) -> Tokens:
    form = {"grant_type": "refresh_token", "refresh_token": tokens.refresh_token}
    body = _token_request(http, config, form, time.time() if now is None else now)
    # Spotify only sometimes rotates the refresh token; keep the old one when it doesn't.
    return Tokens(
        body["access_token"], body.get("refresh_token", tokens.refresh_token), body["expires_at"]
    )


class SpotifyClient:
    """Calls the Web API for one user, refreshing their token and backing off when limited."""

    def __init__(
        self,
        http: httpx.Client,
        config: SpotifyConfig,
        tokens: Tokens,
        on_refresh: Callable[[Tokens], None] = lambda tokens: None,
        clock: Callable[[], float] = time.time,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.http = http
        self.config = config
        self.tokens = tokens
        self.on_refresh = on_refresh
        self.clock = clock
        self.sleep = sleep

    def _refresh(self) -> None:
        self.tokens = refresh_tokens(self.http, self.config, self.tokens, now=self.clock())
        self.on_refresh(self.tokens)

    def get(self, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if self.tokens.expired(self.clock()):
            self._refresh()
        refreshed = False
        for _ in range(MAX_RETRIES + 1):
            response = self.http.get(
                url if url.startswith("http") else f"{API_URL}{url}",
                params=params,
                headers={"Authorization": f"Bearer {self.tokens.access_token}"},
            )
            if response.status_code == 401 and not refreshed:
                self._refresh()
                refreshed = True
                continue
            if response.status_code == 429:
                self.sleep(float(response.headers.get("Retry-After", "1")))
                continue
            if response.status_code != 200:
                raise SpotifyError(f"GET {url} failed: {response.status_code} {response.text}")
            return response.json()
        raise SpotifyError(f"GET {url} still rate limited after {MAX_RETRIES} retries")

    def me(self) -> dict[str, Any]:
        return self.get("/me")

    def recently_played(self, after_ms: int | None = None) -> list[dict[str, Any]]:
        """Plays newer than `after_ms` (Unix ms), oldest first.

        Spotify only keeps the last 50 plays here, which is why the poller has to run often.
        """
        params: dict[str, Any] = {"limit": 50}
        if after_ms is not None:
            params["after"] = after_ms
        items: list[dict[str, Any]] = []
        page: dict[str, Any] | None = self.get("/me/player/recently-played", params)
        while page:
            items.extend(page["items"])
            page = self.get(page["next"]) if page.get("next") else None
        return sorted(items, key=lambda item: item["played_at"])
