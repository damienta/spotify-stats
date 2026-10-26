"""The HTTP API the app talks to, served from Lambda through a function URL.

GET /auth/login?redirect_uri=<app URL>   start "Log in with Spotify"
GET /auth/callback                       Spotify returns here; redirects to the app with ?token=
GET /me                                  who the token belongs to
GET /me/overview?window=4_weeks          totals and top 5s for the home screen, in one call
GET /me/stats                            the stat names available
GET /me/stats/{stat}?window=4_weeks      one stat document, e.g. top_tracks, habits, wrapped
GET /me/now-playing                      the track playing right now, live from Spotify
"""

from __future__ import annotations

import json
import re
import secrets
import time
from collections.abc import Iterator
from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated, Any
from urllib.parse import urlencode, urlparse

import boto3
import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import RedirectResponse
from mangum import Mangum

from stats_api.sessions import SESSION_TTL_S, STATE_TTL_S, InvalidToken, sign, verify
from stats_ingest.spotify import (
    SpotifyClient,
    SpotifyConfig,
    SpotifyError,
    authorize_url,
    exchange_code,
)
from stats_ingest.storage import SSM_PREFIX, UsersTable, env, new_user, spotify_config_from_ssm

# Where the login may send people back to: the Expo dev app, the built app, or a local page.
ALLOWED_REDIRECT_SCHEMES = {"exp", "exps", "spotifystats"}
ALLOWED_REDIRECT_HOSTS = {"localhost", "127.0.0.1"}
STAT_NAME = re.compile(r"^[a-z_]+$")
WINDOW = re.compile(
    r"^(4_weeks|6_months|12_months|all_time|today|this_week|this_month|this_year"
    r"|year_\d{4}|\d{4})$"
)
OVERVIEW_STATS = ("totals", "top_artists", "top_tracks", "top_albums")
OVERVIEW_TOP = 5
# The app asks for now playing every few seconds; answer repeats from memory so a warm Lambda
# doesn't call Spotify more than once per user in this time.
NOW_PLAYING_CACHE_S = 5
# Spotify's answers when a user's grant is missing a scope, revoked or expired.
RECONNECT_STATUSES = {400, 401, 403}

_now_playing_cache: dict[str, tuple[float, dict[str, Any]]] = {}


@dataclass(frozen=True)
class Settings:
    spotify: SpotifyConfig
    session_secret: str


@lru_cache
def get_settings() -> Settings:
    ssm = boto3.client("ssm")
    secret = ssm.get_parameter(Name=f"{SSM_PREFIX}/session_secret", WithDecryption=True)
    return Settings(spotify_config_from_ssm(ssm), secret["Parameter"]["Value"])


@lru_cache
def get_users() -> UsersTable:
    return UsersTable(boto3.resource("dynamodb").Table(env("USERS_TABLE")))


@lru_cache
def get_stats_table() -> Any:
    return boto3.resource("dynamodb").Table(env("STATS_TABLE"))


def get_http() -> Iterator[httpx.Client]:
    with httpx.Client(timeout=15) as http:
        yield http


SettingsDep = Annotated[Settings, Depends(get_settings)]
UsersDep = Annotated[UsersTable, Depends(get_users)]
StatsDep = Annotated[Any, Depends(get_stats_table)]
HttpDep = Annotated[httpx.Client, Depends(get_http)]

app = FastAPI(title="spotify-stats")


def allowed_redirect(uri: str) -> bool:
    url = urlparse(uri)
    if url.scheme in ALLOWED_REDIRECT_SCHEMES:
        return True
    return url.scheme in {"http", "https"} and url.hostname in ALLOWED_REDIRECT_HOSTS


def current_user(settings: SettingsDep, authorization: Annotated[str, Header()] = "") -> str:
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(401, "missing bearer token")
    try:
        return verify(settings.session_secret, token, "session")["sub"]
    except InvalidToken as e:
        raise HTTPException(401, f"invalid token: {e}") from None


UserIdDep = Annotated[str, Depends(current_user)]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/auth/login")
def login(settings: SettingsDep, redirect_uri: str) -> RedirectResponse:
    if not allowed_redirect(redirect_uri):
        raise HTTPException(400, "redirect_uri is not an allowed app address")
    state = sign(
        settings.session_secret,
        {"redirect": redirect_uri, "nonce": secrets.token_urlsafe(8)},
        "state",
        STATE_TTL_S,
    )
    return RedirectResponse(authorize_url(settings.spotify, state), status_code=302)


@app.get("/auth/callback")
def callback(
    settings: SettingsDep,
    users: UsersDep,
    http: HttpDep,
    state: str,
    code: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    try:
        redirect = verify(settings.session_secret, state, "state")["redirect"]
    except InvalidToken as e:
        raise HTTPException(400, f"invalid state: {e}") from None
    if error or not code:
        return _back_to_app(redirect, error=error or "no code")

    tokens = exchange_code(http, settings.spotify, code)
    me = SpotifyClient(http, settings.spotify, tokens).me()
    user = users.get(me["id"])
    if user is None:
        user = new_user(me["id"], me.get("display_name") or me["id"], tokens)
    else:
        user = user.with_tokens(tokens)
        user.display_name = me.get("display_name") or user.display_name
    users.put(user)

    session = sign(settings.session_secret, {"sub": user.user_id}, "session", SESSION_TTL_S)
    return _back_to_app(redirect, token=session)


def _back_to_app(redirect: str, **params: str) -> RedirectResponse:
    separator = "&" if "?" in redirect else "?"
    return RedirectResponse(f"{redirect}{separator}{urlencode(params)}", status_code=302)


@app.get("/me")
def me(user_id: UserIdDep, users: UsersDep) -> dict[str, Any]:
    user = users.get(user_id)
    if user is None:
        raise HTTPException(404, "user not found")
    return {"user_id": user.user_id, "display_name": user.display_name}


def _check_window(window: str | None) -> None:
    if window is not None and not WINDOW.match(window):
        raise HTTPException(400, "unknown window")


@app.get("/me/stats")
def list_stats(user_id: UserIdDep, stats: StatsDep) -> dict[str, Any]:
    names, kwargs = [], {}
    while True:
        page = stats.query(
            KeyConditionExpression="user_id = :u",
            ExpressionAttributeValues={":u": user_id},
            ProjectionExpression="stat_name",
            **kwargs,
        )
        names.extend(i["stat_name"] for i in page["Items"] if not i["stat_name"].startswith("_"))
        if "LastEvaluatedKey" not in page:
            return {"stats": sorted(names)}
        kwargs["ExclusiveStartKey"] = page["LastEvaluatedKey"]


@app.get("/me/stats/{stat}")
def get_stat(
    user_id: UserIdDep, stats: StatsDep, stat: str, window: str | None = None
) -> dict[str, Any]:
    if not STAT_NAME.match(stat):
        raise HTTPException(400, "unknown stat")
    _check_window(window)
    stat_name = stat if window is None else f"{stat}#{window}"
    item = stats.get_item(Key={"user_id": user_id, "stat_name": stat_name}).get("Item")
    if item is None:
        raise HTTPException(404, f"{stat_name} isn't available yet")
    return {
        "stat_name": stat_name,
        "generated_at": item["generated_at"],
        "data": json.loads(item["data"]),
    }


@app.get("/me/overview")
def overview(
    user_id: UserIdDep, stats: StatsDep, window: Annotated[str, Query()] = "4_weeks"
) -> dict[str, Any]:
    _check_window(window)
    keys = [{"user_id": user_id, "stat_name": f"{s}#{window}"} for s in OVERVIEW_STATS]
    response = stats.meta.client.batch_get_item(RequestItems={stats.name: {"Keys": keys}})
    items = {i["stat_name"].split("#")[0]: i for i in response["Responses"][stats.name]}
    if "totals" not in items:
        raise HTTPException(404, "stats aren't ready yet: they're built hourly")
    result: dict[str, Any] = {"window": window, "generated_at": items["totals"]["generated_at"]}
    for name in OVERVIEW_STATS:
        data = json.loads(items[name]["data"]) if name in items else None
        result[name] = data[:OVERVIEW_TOP] if isinstance(data, list) else data
    return result


def _spotify(
    user_id: str, settings: Settings, users: UsersTable, http: httpx.Client
) -> SpotifyClient:
    user = users.get(user_id)
    if user is None:
        raise HTTPException(404, "user not found")
    return SpotifyClient(http, settings.spotify, user.tokens, on_refresh=users.token_saver(user))


def _spotify_failed(e: SpotifyError) -> HTTPException:
    if e.status in RECONNECT_STATUSES:
        return HTTPException(403, "reconnect Spotify: log in again to allow this")
    return HTTPException(502, "Spotify didn't answer, try again shortly")


def track_summary(item: dict[str, Any]) -> dict[str, Any]:
    """The parts of a Spotify track object the app shows."""
    album = item.get("album") or {}
    images = album.get("images") or []
    return {
        "id": item.get("id"),
        "name": item.get("name"),
        "artists": [a["name"] for a in item.get("artists", [])],
        "album": album.get("name"),
        "image": images[0]["url"] if images else None,
        "duration_ms": item.get("duration_ms"),
        "url": (item.get("external_urls") or {}).get("spotify"),
    }


@app.get("/me/now-playing")
def now_playing(
    user_id: UserIdDep, settings: SettingsDep, users: UsersDep, http: HttpDep
) -> dict[str, Any]:
    cached = _now_playing_cache.get(user_id)
    if cached and time.monotonic() - cached[0] < NOW_PLAYING_CACHE_S:
        return cached[1]
    try:
        playing = _spotify(user_id, settings, users, http).currently_playing()
    except SpotifyError as e:
        raise _spotify_failed(e) from None
    result: dict[str, Any] = {"is_playing": False, "progress_ms": None, "track": None}
    if playing:
        result = {
            "is_playing": bool(playing.get("is_playing")),
            "progress_ms": playing.get("progress_ms"),
            "track": track_summary(playing["item"]),
        }
    _now_playing_cache[user_id] = (time.monotonic(), result)
    return result


handler = Mangum(app, lifespan="off")
