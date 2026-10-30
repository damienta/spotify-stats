import json
from urllib.parse import parse_qs, urlparse

import boto3
import httpx
import pytest
from fastapi.testclient import TestClient

from stats_api import app as app_module
from stats_api.app import (
    Settings,
    app,
    get_bucket,
    get_http,
    get_s3,
    get_settings,
    get_stats_table,
    get_users,
)
from stats_api.sessions import sign
from stats_ingest.spotify import SpotifyConfig, Tokens
from stats_ingest.storage import UsersTable, new_user

SETTINGS = Settings(
    SpotifyConfig("client-id", "client-secret", "https://api.example/auth/callback"),
    session_secret="test-secret",
)
APP_REDIRECT = "exp://192.168.1.5:8081/--/auth"


TRACK = {
    "id": "t1",
    "name": "Night drive",
    "artists": [{"name": "Nova Lane"}],
    "album": {"name": "Roads", "images": [{"url": "https://i.scdn.co/image/big"}]},
    "duration_ms": 200_000,
    "external_urls": {"spotify": "https://open.spotify.com/track/t1"},
}
# What the fake Spotify answers for each player endpoint; tests change these.
PLAYER: dict[str, httpx.Response] = {}
CALLS: list[str] = []


def fake_spotify(request):
    CALLS.append(request.url.path)
    if request.url.host == "accounts.spotify.com":
        return httpx.Response(
            200, json={"access_token": "a", "refresh_token": "r", "expires_in": 3600}
        )
    if request.url.path in PLAYER:
        return PLAYER[request.url.path]
    return httpx.Response(200, json={"id": "u1", "display_name": "Damien"})


@pytest.fixture
def client(aws):
    stats = boto3.resource("dynamodb").Table("stats")
    users = UsersTable(boto3.resource("dynamodb").Table("users"))

    def http():
        with httpx.Client(transport=httpx.MockTransport(fake_spotify)) as c:
            yield c

    PLAYER.clear()
    CALLS.clear()
    app_module._now_playing_cache.clear()
    app.dependency_overrides = {
        get_settings: lambda: SETTINGS,
        get_users: lambda: users,
        get_stats_table: lambda: stats,
        get_http: http,
        get_s3: lambda: boto3.client("s3"),
        get_bucket: lambda: "data",
    }
    yield TestClient(app, follow_redirects=False)
    app.dependency_overrides = {}


def auth(user_id="u1"):
    token = sign(SETTINGS.session_secret, {"sub": user_id}, "session", ttl_s=60)
    return {"Authorization": f"Bearer {token}"}


def put_stat(stat_name, data, user_id="u1"):
    boto3.resource("dynamodb").Table("stats").put_item(
        Item={
            "user_id": user_id,
            "stat_name": stat_name,
            "generated_at": "2026-10-25T18:00:00+00:00",
            "data": json.dumps(data),
        }
    )


def test_login_round_trip_creates_the_user_and_returns_a_session(client):
    login = client.get("/auth/login", params={"redirect_uri": APP_REDIRECT})
    assert login.status_code == 302
    spotify = parse_qs(urlparse(login.headers["location"]).query)
    assert spotify["redirect_uri"] == ["https://api.example/auth/callback"]

    callback = client.get("/auth/callback", params={"code": "c", "state": spotify["state"][0]})

    assert callback.status_code == 302
    back = urlparse(callback.headers["location"])
    assert f"{back.scheme}://{back.netloc}{back.path}" == APP_REDIRECT
    token = parse_qs(back.query)["token"][0]
    assert client.get("/me", headers={"Authorization": f"Bearer {token}"}).json() == {
        "user_id": "u1",
        "display_name": "Damien",
    }


def test_login_keeps_an_existing_users_cursor(client):
    users = UsersTable(boto3.resource("dynamodb").Table("users"))
    user = new_user("u1", "Old name", Tokens("old", "old", 0))
    user.cursor_ms = 123
    users.put(user)
    state = parse_qs(
        urlparse(
            client.get("/auth/login", params={"redirect_uri": APP_REDIRECT}).headers["location"]
        ).query
    )["state"][0]

    client.get("/auth/callback", params={"code": "c", "state": state})

    saved = users.get("u1")
    assert (saved.cursor_ms, saved.access_token, saved.display_name) == (123, "a", "Damien")


@pytest.mark.parametrize("uri", ["https://evil.example/steal", "javascript:alert(1)"])
def test_login_refuses_other_redirects(client, uri):
    assert client.get("/auth/login", params={"redirect_uri": uri}).status_code == 400


@pytest.mark.parametrize(
    ("uri", "allowed"),
    [
        ("https://stats.pages.dev/auth", True),
        ("https://1a2b3c.stats.pages.dev/auth", True),  # a preview deployment
        ("http://stats.pages.dev/auth", False),
        ("https://evilstats.pages.dev/auth", False),
        ("https://pages.dev/auth", False),
        ("https://stats.pages.dev.evil.example/auth", False),
    ],
)
def test_login_allows_the_hosted_app(client, monkeypatch, uri, allowed):
    monkeypatch.setenv("APP_HOSTS", "stats.pages.dev")
    status = client.get("/auth/login", params={"redirect_uri": uri}).status_code
    assert (status == 302) is allowed


def test_callback_rejects_forged_state(client):
    assert client.get("/auth/callback", params={"code": "c", "state": "x.y"}).status_code == 400


def test_denied_login_goes_back_to_the_app_with_the_error(client):
    state = sign(SETTINGS.session_secret, {"redirect": APP_REDIRECT}, "state", ttl_s=60)

    response = client.get("/auth/callback", params={"error": "access_denied", "state": state})

    assert response.headers["location"] == f"{APP_REDIRECT}?error=access_denied"


def test_stats_need_a_valid_token(client):
    assert client.get("/me/stats").status_code == 401
    assert client.get("/me/stats", headers={"Authorization": "Bearer x.y"}).status_code == 401


def test_get_one_stat(client):
    put_stat("top_tracks#4_weeks", [{"name": "Song", "streams": 3}])
    put_stat("streaks", {"longest": {"days": 863}})

    response = client.get("/me/stats/top_tracks", params={"window": "4_weeks"}, headers=auth())

    assert response.json()["data"] == [{"name": "Song", "streams": 3}]
    assert client.get("/me/stats/streaks", headers=auth()).json()["data"]["longest"]["days"] == 863
    assert (
        client.get(
            "/me/stats/top_tracks", params={"window": "all_time"}, headers=auth()
        ).status_code
        == 404
    )
    assert (
        client.get("/me/stats/top_tracks", params={"window": "../x"}, headers=auth()).status_code
        == 400
    )


def test_users_only_see_their_own_stats(client):
    put_stat("streaks", {"longest": {"days": 1}}, user_id="someone-else")

    assert client.get("/me/stats/streaks", headers=auth()).status_code == 404


def test_list_stats_hides_internal_items(client):
    put_stat("streaks", {})
    put_stat("_build", {})

    assert client.get("/me/stats", headers=auth()).json() == {"stats": ["streaks"]}


def test_overview_bundles_totals_and_top_fives(client):
    put_stat("totals#4_weeks", {"streams": 3160})
    put_stat("top_artists#4_weeks", [{"name": f"A{n}"} for n in range(50)])
    put_stat("top_tracks#4_weeks", [{"name": "T"}])

    body = client.get("/me/overview", headers=auth()).json()

    assert body["totals"] == {"streams": 3160}
    assert [a["name"] for a in body["top_artists"]] == ["A0", "A1", "A2", "A3", "A4"]
    assert body["top_albums"] is None


def test_overview_before_the_first_build(client):
    assert client.get("/me/overview", headers=auth()).status_code == 404


def put_user():
    UsersTable(boto3.resource("dynamodb").Table("users")).put(
        new_user("u1", "Damien", Tokens("a", "r", 9e9))
    )


NOW_PLAYING = "/v1/me/player/currently-playing"


def test_now_playing_returns_the_track(client):
    put_user()
    PLAYER[NOW_PLAYING] = httpx.Response(
        200, json={"is_playing": True, "progress_ms": 61_000, "item": TRACK}
    )

    body = client.get("/me/now-playing", headers=auth()).json()

    assert body == {
        "is_playing": True,
        "progress_ms": 61_000,
        "track": {
            "id": "t1",
            "name": "Night drive",
            "artists": ["Nova Lane"],
            "album": "Roads",
            "image": "https://i.scdn.co/image/big",
            "duration_ms": 200_000,
            "url": "https://open.spotify.com/track/t1",
        },
    }


def test_now_playing_when_nothing_plays(client):
    put_user()
    PLAYER[NOW_PLAYING] = httpx.Response(204)

    body = client.get("/me/now-playing", headers=auth()).json()

    assert body == {"is_playing": False, "progress_ms": None, "track": None}


def test_now_playing_is_cached_for_a_few_seconds(client):
    put_user()
    PLAYER[NOW_PLAYING] = httpx.Response(204)

    client.get("/me/now-playing", headers=auth())
    client.get("/me/now-playing", headers=auth())

    assert CALLS.count(NOW_PLAYING) == 1


def test_now_playing_asks_to_reconnect_without_the_scope(client):
    put_user()
    PLAYER[NOW_PLAYING] = httpx.Response(403, json={"error": {"message": "Permissions missing"}})

    response = client.get("/me/now-playing", headers=auth())

    assert response.status_code == 403
    assert "reconnect" in response.json()["detail"]


RECENT = "/v1/me/player/recently-played"


def played(n, at):
    return {"played_at": at, "track": {**TRACK, "id": f"t{n}", "name": f"Song {n}"}}


def stored_keys():
    listing = boto3.client("s3").list_objects_v2(Bucket="data", Prefix="listens/")
    return [o["Key"] for o in listing.get("Contents", [])]


def test_recent_is_newest_first_and_stores_new_plays(client):
    put_user()
    PLAYER[RECENT] = httpx.Response(
        200,
        json={
            "items": [played(1, "2026-10-26T09:00:00.000Z"), played(2, "2026-10-26T09:04:00.000Z")],
            "next": None,
        },
    )

    body = client.get("/me/recent", params={"limit": 1}, headers=auth()).json()

    assert body == {
        "items": [
            {
                "played_at": "2026-10-26T09:04:00.000Z",
                "track": {
                    "id": "t2",
                    "name": "Song 2",
                    "artists": ["Nova Lane"],
                    "album": "Roads",
                    "image": "https://i.scdn.co/image/big",
                    "duration_ms": 200_000,
                    "url": "https://open.spotify.com/track/t1",
                },
            }
        ]
    }
    assert len(stored_keys()) == 1
    users = UsersTable(boto3.resource("dynamodb").Table("users"))
    assert users.get("u1").cursor_ms == 1793005440000

    client.get("/me/recent", headers=auth())  # nothing new the second time
    assert len(stored_keys()) == 1


def test_recent_rejects_silly_limits(client):
    assert client.get("/me/recent", params={"limit": 500}, headers=auth()).status_code == 422


def test_delete_me_removes_everything_of_that_user(client):
    put_user()
    UsersTable(boto3.resource("dynamodb").Table("users")).put(
        new_user("u2", "Friend", Tokens("a", "r", 9e9))
    )
    stats = boto3.resource("dynamodb").Table("stats")
    for user in ("u1", "u2"):
        stats.put_item(Item={"user_id": user, "stat_name": "totals#4_weeks", "data": {}})
        stats.put_item(Item={"user_id": user, "stat_name": "_meta", "data": {}})
    s3 = boto3.client("s3")
    for key in (
        "listens/user=u1/source=api/1.jsonl",
        "listens/user=u1/source=export/export.parquet",
        "raw/source=api/user=u1/date=2026-10-28/1.json",
        "uploads/user=u1/export.zip",
        "listens/user=u2/source=api/1.jsonl",
        "listens/user=u10/source=api/1.jsonl",
        "catalog/spotify.json",
    ):
        s3.put_object(Bucket="data", Key=key, Body=b"x")

    assert client.delete("/me", headers=auth()).status_code == 204

    users = UsersTable(boto3.resource("dynamodb").Table("users"))
    assert users.get("u1") is None
    assert users.get("u2") is not None
    left = {(i["user_id"], i["stat_name"]) for i in stats.scan()["Items"]}
    assert left == {("u2", "totals#4_weeks"), ("u2", "_meta")}
    keys = {o["Key"] for o in s3.list_objects_v2(Bucket="data")["Contents"]}
    # Other users (even one whose id starts the same) and the shared picture cache stay.
    assert keys == {
        "listens/user=u2/source=api/1.jsonl",
        "listens/user=u10/source=api/1.jsonl",
        "catalog/spotify.json",
    }
    assert client.get("/me", headers=auth()).status_code == 404


def test_delete_me_needs_a_session(client):
    assert client.delete("/me").status_code == 401
