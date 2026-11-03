"""The HTTP API the app talks to, served from Lambda through a function URL.

GET /auth/login?redirect_uri=<app URL>   start "Log in with Spotify"
GET /auth/callback                       Spotify returns here; redirects to the app with ?token=
GET /me                                  who the token belongs to, and their settings
PATCH /me {share_with_friends}           change a setting
GET /me/overview?window=4_weeks          totals and top 5s for the home screen, in one call
GET /me/stats                            the stat names available
GET /me/stats/{stat}?window=4_weeks      one stat document, e.g. top_tracks, habits, wrapped
GET /me/artist?name=<artist>             one of your top artists' pages
GET /me/now-playing                      the track playing right now, live from Spotify
GET /me/recent?limit=20                  recently played tracks, live from Spotify
DELETE /me                               delete the account and every play and stat stored

GET /friends                             my friends
GET /friends/invite                      my invite token (the app makes it into a link)
POST /friends/invite/reset               a new token; every old link stops working
POST /friends/invite/preview {invite}    who a link is from, so the app can ask "Add Alice?"
POST /friends {invite}                   accept a link: friends both ways
DELETE /friends/{id}                     remove a friend, both ways
GET /friends/{id}/summary                a friend's top 10s, minutes this week, streak
GET /friends/{id}/compare                taste match %, artists you both love, theirs new to you
GET /friends/leaderboard                 me and my friends by minutes this week
"""

from __future__ import annotations

import json
import logging
import os
import re
import secrets
import time
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from typing import Annotated, Any
from urllib.parse import urlencode, urlparse

import boto3
import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import RedirectResponse
from mangum import Mangum
from pydantic import BaseModel, Field

from stats_api.friends import (
    INVITE_TTL_S,
    MAX_FRIENDS,
    SHOWN,
    AlreadyFriends,
    FriendsTable,
    NotFriends,
    both_love,
    new_to_you,
    public_row,
    taste_match,
)
from stats_api.sessions import SESSION_TTL_S, STATE_TTL_S, InvalidToken, sign, verify
from stats_ingest.poller import store_plays
from stats_ingest.spotify import (
    SpotifyClient,
    SpotifyConfig,
    SpotifyError,
    authorize_url,
    exchange_code,
)
from stats_ingest.storage import (
    SSM_PREFIX,
    User,
    UsersTable,
    artist_stat_name,
    delete_prefix,
    env,
    new_user,
    spotify_config_from_ssm,
    user_prefixes,
)

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

RECENT_MAX = 50

log = logging.getLogger()

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


@lru_cache
def get_friends() -> FriendsTable:
    return FriendsTable(boto3.resource("dynamodb").Table(env("FRIENDS_TABLE")))


@lru_cache
def get_s3() -> Any:
    return boto3.client("s3")


def get_bucket() -> str:
    return env("DATA_BUCKET")


def get_http() -> Iterator[httpx.Client]:
    with httpx.Client(timeout=15) as http:
        yield http


SettingsDep = Annotated[Settings, Depends(get_settings)]
UsersDep = Annotated[UsersTable, Depends(get_users)]
StatsDep = Annotated[Any, Depends(get_stats_table)]
FriendsDep = Annotated[FriendsTable, Depends(get_friends)]
HttpDep = Annotated[httpx.Client, Depends(get_http)]
S3Dep = Annotated[Any, Depends(get_s3)]
BucketDep = Annotated[str, Depends(get_bucket)]

app = FastAPI(title="spotify-stats")


def hosted_apps() -> set[str]:
    """The hosted web app's addresses, from APP_HOSTS (comma-separated, e.g. stats.pages.dev)."""
    return {h.strip().lower() for h in os.environ.get("APP_HOSTS", "").split(",") if h.strip()}


def allowed_redirect(uri: str) -> bool:
    """Login only hands a session token back to our own apps: the phone app, local development,
    and the hosted site over https, including its preview deployments (<id>.<host>)."""
    url = urlparse(uri)
    if url.scheme in ALLOWED_REDIRECT_SCHEMES:
        return True
    host = url.hostname or ""
    if url.scheme in {"http", "https"} and host in ALLOWED_REDIRECT_HOSTS:
        return True
    return url.scheme == "https" and any(
        host == app or host.endswith(f".{app}") for app in hosted_apps()
    )


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
    return {
        "user_id": user.user_id,
        "display_name": user.display_name,
        "share_with_friends": user.share_with_friends,
    }


class MeChanges(BaseModel):
    share_with_friends: bool | None = None


@app.patch("/me")
def update_me(user_id: UserIdDep, users: UsersDep, changes: MeChanges) -> dict[str, Any]:
    if changes.share_with_friends is not None:
        try:
            users.set_sharing(user_id, changes.share_with_friends)
        except users.table.meta.client.exceptions.ConditionalCheckFailedException:
            raise HTTPException(404, "user not found") from None
    return me(user_id, users)


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
    return _document(item)


@app.get("/me/artist")
def get_artist(
    user_id: UserIdDep, stats: StatsDep, name: Annotated[str, Query(min_length=1, max_length=300)]
) -> dict[str, Any]:
    key = {"user_id": user_id, "stat_name": artist_stat_name(name)}
    item = stats.get_item(Key=key).get("Item")
    if item is None:
        raise HTTPException(404, "only your top artists have a page")
    return _document(item)


def _document(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "stat_name": item["stat_name"],
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


def _user(user_id: str, users: UsersTable) -> User:
    user = users.get(user_id)
    if user is None:
        raise HTTPException(404, "user not found")
    return user


def _spotify(
    user_id: str, settings: Settings, users: UsersTable, http: httpx.Client
) -> SpotifyClient:
    user = _user(user_id, users)
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


@app.get("/me/recent")
def recent(
    user_id: UserIdDep,
    settings: SettingsDep,
    users: UsersDep,
    http: HttpDep,
    s3: S3Dep,
    bucket: BucketDep,
    limit: Annotated[int, Query(ge=1, le=RECENT_MAX)] = 20,
) -> dict[str, Any]:
    """The last plays, newest first. Plays the poller hasn't stored yet are stored too, so
    opening the app makes stats fresher."""
    user = _user(user_id, users)
    client = SpotifyClient(http, settings.spotify, user.tokens, on_refresh=users.token_saver(user))
    try:
        items = client.recently_played()
    except SpotifyError as e:
        raise _spotify_failed(e) from None
    try:
        store_plays(items, user, users=users, s3=s3, bucket=bucket, now=datetime.now(UTC))
    except Exception:
        # Showing the list matters more; the poller will store these plays anyway.
        log.exception("storing recent plays for %s failed", user_id)
    newest_first = sorted(items, key=lambda i: i["played_at"], reverse=True)[:limit]
    return {
        "items": [
            {"played_at": i["played_at"], "track": track_summary(i["track"])} for i in newest_first
        ]
    }


@app.delete("/me", status_code=204)
def delete_me(
    user_id: UserIdDep,
    users: UsersDep,
    stats: StatsDep,
    friends: FriendsDep,
    s3: S3Dep,
    bucket: BucketDep,
) -> None:
    """Delete the account. The user record goes first, so the poller and the stats job stop
    picking this user up; then their friendships, both ways; then their stat documents; then
    every file of plays in S3. The shared picture cache holds no personal data, so it stays."""
    users.delete(user_id)
    _now_playing_cache.pop(user_id, None)
    friendships = friends.remove_all(user_id)
    stat_names, kwargs = [], {}
    while True:
        page = stats.query(
            KeyConditionExpression="user_id = :u",
            ExpressionAttributeValues={":u": user_id},
            ProjectionExpression="stat_name",
            **kwargs,
        )
        stat_names.extend(i["stat_name"] for i in page["Items"])
        if "LastEvaluatedKey" not in page:
            break
        kwargs["ExclusiveStartKey"] = page["LastEvaluatedKey"]
    with stats.batch_writer() as batch:
        for name in stat_names:
            batch.delete_item(Key={"user_id": user_id, "stat_name": name})
    files = sum(delete_prefix(s3, bucket, prefix) for prefix in user_prefixes(user_id))
    log.info(
        "deleted user %s: %d friendships, %d stats, %d files",
        user_id,
        friendships,
        len(stat_names),
        files,
    )


# Friends. Who "I" am always comes from the session token, never from the request body.


class Invite(BaseModel):
    # Tokens are a couple of hundred characters; the cap stops anyone posting megabytes.
    invite: str = Field(min_length=1, max_length=1000)


def _invite_token(settings: Settings, user_id: str, nonce: str) -> dict[str, str]:
    token = sign(settings.session_secret, {"sub": user_id, "n": nonce}, "invite", INVITE_TTL_S)
    return {"invite": token}


def _inviter(settings: Settings, users: UsersTable, invite: str) -> User:
    """Who sent a link. Forged, expired and reset links, and links from deleted accounts, all
    give the same 404, so a link reveals nothing unless it's live."""
    try:
        claims = verify(settings.session_secret, invite, "invite")
    except InvalidToken:
        raise HTTPException(404, "this invite link isn't valid any more") from None
    inviter = users.get(str(claims.get("sub", "")))
    if inviter is None or not inviter.invite_nonce or claims.get("n") != inviter.invite_nonce:
        raise HTTPException(404, "this invite link isn't valid any more")
    return inviter


@app.get("/friends/invite")
def get_invite(user_id: UserIdDep, settings: SettingsDep, users: UsersDep) -> dict[str, str]:
    return _invite_token(settings, user_id, users.invite_nonce(user_id))


@app.post("/friends/invite/reset")
def reset_invite(user_id: UserIdDep, settings: SettingsDep, users: UsersDep) -> dict[str, str]:
    return _invite_token(settings, user_id, users.invite_nonce(user_id, reset=True))


# POST rather than GET /friends/invite/{invite}: the token stays out of URLs, and so out of
# any request logs (the Ticketmaster key once leaked through logged URLs).
@app.post("/friends/invite/preview")
def preview_invite(
    user_id: UserIdDep, settings: SettingsDep, users: UsersDep, friends: FriendsDep, body: Invite
) -> dict[str, Any]:
    inviter = _inviter(settings, users, body.invite)
    return {
        "display_name": inviter.display_name,
        "is_you": inviter.user_id == user_id,
        "already_friends": friends.get(user_id, inviter.user_id) is not None,
    }


@app.post("/friends", status_code=201)
def accept_invite(
    user_id: UserIdDep, settings: SettingsDep, users: UsersDep, friends: FriendsDep, body: Invite
) -> dict[str, Any]:
    inviter = _inviter(settings, users, body.invite)
    if inviter.user_id == user_id:
        raise HTTPException(400, "that's your own invite link")
    if friends.get(user_id, inviter.user_id) is not None:
        raise HTTPException(409, "you're already friends")
    if max(friends.count(user_id), friends.count(inviter.user_id)) >= MAX_FRIENDS:
        raise HTTPException(422, f"friends are limited to {MAX_FRIENDS} each")
    try:
        since = friends.add(user_id, inviter.user_id)
    except AlreadyFriends:
        raise HTTPException(409, "you're already friends") from None
    return {"user_id": inviter.user_id, "display_name": inviter.display_name, "since": since}


@app.get("/friends")
def list_friends(
    user_id: UserIdDep, users: UsersDep, stats: StatsDep, friends: FriendsDep
) -> dict[str, Any]:
    """My friends, by name. Minutes this week only for friends who share."""
    friendships = friends.of(user_id)
    people = users.get_many(f.friend_id for f in friendships)
    minutes = _minutes_this_week(stats, [i for i, p in people.items() if p.share_with_friends])
    result = [
        {
            "user_id": f.friend_id,
            "display_name": people[f.friend_id].display_name,
            "since": f.since,
            "sharing": f.friend_id in minutes,
            "minutes_this_week": minutes.get(f.friend_id),
        }
        # A friend whose account is mid-deletion has no user any more: leave them out.
        for f in friendships
        if f.friend_id in people
    ]
    return {"friends": sorted(result, key=lambda f: f["display_name"].casefold())}


@app.delete("/friends/{friend_id}", status_code=204)
def remove_friend(user_id: UserIdDep, friends: FriendsDep, friend_id: str) -> None:
    try:
        friends.remove(user_id, friend_id)
    except NotFriends:
        raise HTTPException(404, "not found") from None


def _minutes_this_week(stats: Any, user_ids: list[str]) -> dict[str, int]:
    """Minutes this week for each user, from their `totals#this_week` document. Users whose
    stats haven't been built yet count as 0."""
    docs = _stat_docs(stats, [(u, "totals#this_week") for u in user_ids])
    return {u: round(docs.get((u, "totals#this_week"), {}).get("hours", 0) * 60) for u in user_ids}


def _stat_docs(stats: Any, keys: list[tuple[str, str]]) -> dict[tuple[str, str], Any]:
    """Several users' stat documents by (user_id, stat_name), in BatchGetItems of up to 100."""
    found: dict[tuple[str, str], Any] = {}
    unique = list(dict.fromkeys(keys))
    for start in range(0, len(unique), 100):
        chunk = [{"user_id": u, "stat_name": n} for u, n in unique[start : start + 100]]
        request = {stats.name: {"Keys": chunk}}
        while request:
            response = stats.meta.client.batch_get_item(RequestItems=request)
            for item in response["Responses"].get(stats.name, []):
                found[(item["user_id"], item["stat_name"])] = json.loads(item["data"])
            request = response.get("UnprocessedKeys") or {}
    return found


def friend(user_id: UserIdDep, users: UsersDep, friends: FriendsDep, friend_id: str) -> User:
    """The friend a `/friends/{id}/...` route is about. Every such route depends on this, so
    the check can't be forgotten on one of them.

    Not friends, no such user, and a friend who has turned sharing off all give the same 404
    (not 403), so nobody can learn whether an account exists or who shares."""
    if friend_id == user_id or friends.get(user_id, friend_id) is None:
        raise HTTPException(404, "not found")
    them = users.get(friend_id)
    if them is None or not them.share_with_friends:
        raise HTTPException(404, "not found")
    return them


FriendDep = Annotated[User, Depends(friend)]


@app.get("/friends/leaderboard")
def leaderboard(
    user_id: UserIdDep, users: UsersDep, stats: StatsDep, friends: FriendsDep
) -> dict[str, Any]:
    """Me and my friends who share, by minutes this week. I'm always on my own board."""
    people = users.get_many([user_id, *(f.friend_id for f in friends.of(user_id))])
    board = [i for i, p in people.items() if i == user_id or p.share_with_friends]
    minutes = _minutes_this_week(stats, board)
    rows = sorted(
        (
            {
                "user_id": i,
                "display_name": people[i].display_name,
                "minutes": minutes[i],
                "is_you": i == user_id,
            }
            for i in board
        ),
        key=lambda r: (-r["minutes"], r["display_name"].casefold()),
    )
    return {"leaderboard": [{"rank": n, **r} for n, r in enumerate(rows, 1)]}


@app.get("/friends/{friend_id}/summary")
def friend_summary(them: FriendDep, stats: StatsDep) -> dict[str, Any]:
    """Only these fields, never their full history, recent plays or listening clock. A friend
    whose stats aren't built yet gets empty lists and `generated_at: null`."""
    names = ["top_artists#4_weeks", "top_tracks#4_weeks", "totals#this_week", "streaks"]
    docs = _stat_docs(stats, [(them.user_id, n) for n in names])
    doc = {n: docs.get((them.user_id, n)) for n in names}
    return {
        "user_id": them.user_id,
        "display_name": them.display_name,
        "ready": doc["totals#this_week"] is not None,
        "top_artists": [public_row(r) for r in (doc["top_artists#4_weeks"] or [])[:SHOWN]],
        "top_tracks": [public_row(r) for r in (doc["top_tracks#4_weeks"] or [])[:SHOWN]],
        "minutes_this_week": round((doc["totals#this_week"] or {}).get("hours", 0) * 60),
        "streak_days": ((doc["streaks"] or {}).get("current") or {}).get("days", 0),
    }


@app.get("/friends/{friend_id}/compare")
def friend_compare(user_id: UserIdDep, them: FriendDep, stats: StatsDep) -> dict[str, Any]:
    """Compared on each person's top 100 artists of the last 12 months. "New to you" also
    skips anything in your all-time list, so it's artists you really haven't been playing."""
    keys = [
        (user_id, "top_artists#12_months"),
        (user_id, "top_artists#all_time"),
        (them.user_id, "top_artists#12_months"),
    ]
    docs = _stat_docs(stats, keys)
    mine, mine_ever, theirs = (docs.get(k) or [] for k in keys)
    return {
        "user_id": them.user_id,
        "display_name": them.display_name,
        "taste_match": taste_match(mine, theirs),
        "both_love": both_love(mine, theirs),
        "new_to_you": new_to_you(theirs, mine + mine_ever),
    }


handler = Mangum(app, lifespan="off")
