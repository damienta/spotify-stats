import json

import boto3
import pytest
from fastapi.testclient import TestClient

from stats_api.app import (
    Settings,
    app,
    get_bucket,
    get_friends,
    get_s3,
    get_settings,
    get_stats_table,
    get_users,
)
from stats_api.friends import MAX_FRIENDS, AlreadyFriends, FriendsTable
from stats_api.sessions import sign
from stats_ingest.spotify import SpotifyConfig, Tokens
from stats_ingest.storage import UsersTable, new_user

SETTINGS = Settings(
    SpotifyConfig("client-id", "client-secret", "https://api.example/auth/callback"),
    session_secret="test-secret",
)


@pytest.fixture
def client(aws):
    dynamodb = boto3.resource("dynamodb")
    app.dependency_overrides = {
        get_settings: lambda: SETTINGS,
        get_users: lambda: users(),
        get_stats_table: lambda: dynamodb.Table("stats"),
        get_friends: lambda: friends(),
        get_s3: lambda: boto3.client("s3"),
        get_bucket: lambda: "data",
    }
    for user_id, name in (("alice", "Alice"), ("bob", "Bob"), ("carol", "Carol")):
        users().put(new_user(user_id, name, Tokens("a", "r", 9e9)))
    yield TestClient(app)
    app.dependency_overrides = {}


def users():
    return UsersTable(boto3.resource("dynamodb").Table("users"))


def friends():
    return FriendsTable(boto3.resource("dynamodb").Table("friends"))


def friend_items():
    items = boto3.resource("dynamodb").Table("friends").scan()["Items"]
    return {(i["user_id"], i["friend_id"]) for i in items}


def auth(user_id):
    token = sign(SETTINGS.session_secret, {"sub": user_id}, "session", ttl_s=60)
    return {"Authorization": f"Bearer {token}"}


def invite_of(client, user_id):
    return client.get("/friends/invite", headers=auth(user_id)).json()["invite"]


def befriend(client, a, b):
    response = client.post("/friends", json={"invite": invite_of(client, a)}, headers=auth(b))
    assert response.status_code == 201, response.text


def put_stat(user_id, stat_name, data):
    boto3.resource("dynamodb").Table("stats").put_item(
        Item={
            "user_id": user_id,
            "stat_name": stat_name,
            "generated_at": "2026-11-02T18:00:00+00:00",
            "data": json.dumps(data),
        }
    )


def test_accepting_an_invite_makes_friends_both_ways(client):
    invite = invite_of(client, "alice")

    preview = client.post("/friends/invite/preview", json={"invite": invite}, headers=auth("bob"))
    accepted = client.post("/friends", json={"invite": invite}, headers=auth("bob"))

    assert preview.json() == {"display_name": "Alice", "is_you": False, "already_friends": False}
    assert accepted.status_code == 201
    assert accepted.json()["display_name"] == "Alice"
    assert friend_items() == {("alice", "bob"), ("bob", "alice")}


def test_the_invite_is_the_same_until_reset(client):
    assert invite_of(client, "alice") == invite_of(client, "alice")


def test_accepting_twice_is_a_conflict(client):
    befriend(client, "alice", "bob")

    again = client.post(
        "/friends", json={"invite": invite_of(client, "alice")}, headers=auth("bob")
    )
    preview = client.post(
        "/friends/invite/preview", json={"invite": invite_of(client, "alice")}, headers=auth("bob")
    )

    assert again.status_code == 409
    assert preview.json()["already_friends"] is True


def test_a_race_past_the_check_still_cant_double_up(client):
    friends().add("alice", "bob")

    with pytest.raises(AlreadyFriends):
        friends().add("bob", "alice")
    assert friend_items() == {("alice", "bob"), ("bob", "alice")}


def test_your_own_link_is_refused(client):
    invite = invite_of(client, "alice")

    response = client.post("/friends", json={"invite": invite}, headers=auth("alice"))
    preview = client.post("/friends/invite/preview", json={"invite": invite}, headers=auth("alice"))

    assert response.status_code == 400
    assert preview.json()["is_you"] is True
    assert friend_items() == set()


def test_forged_expired_and_wrong_purpose_links_are_not_found(client):
    nonce = users().invite_nonce("alice")
    expired = sign(SETTINGS.session_secret, {"sub": "alice", "n": nonce}, "invite", ttl_s=-1)
    session = sign(SETTINGS.session_secret, {"sub": "alice", "n": nonce}, "session", ttl_s=60)
    forged = sign("not-the-secret", {"sub": "alice", "n": nonce}, "invite", ttl_s=60)

    for invite in (expired, session, forged, "x.y"):
        response = client.post("/friends", json={"invite": invite}, headers=auth("bob"))
        assert response.status_code == 404
    assert friend_items() == set()


def test_resetting_the_link_kills_the_old_one(client):
    old = invite_of(client, "alice")

    new = client.post("/friends/invite/reset", headers=auth("alice")).json()["invite"]

    assert new != old
    assert client.post("/friends", json={"invite": old}, headers=auth("bob")).status_code == 404
    assert client.post("/friends", json={"invite": new}, headers=auth("bob")).status_code == 201


def test_a_link_from_a_deleted_account_is_not_found(client):
    invite = invite_of(client, "alice")
    users().delete("alice")

    assert client.post("/friends", json={"invite": invite}, headers=auth("bob")).status_code == 404


def test_login_keeps_the_friend_settings(client):
    nonce = users().invite_nonce("alice")
    users().set_sharing("alice", False)

    user = users().get("alice").with_tokens(Tokens("new", "new", 1))
    users().put(user)  # what the login callback does

    saved = users().get("alice")
    assert (saved.invite_nonce, saved.share_with_friends) == (nonce, False)


def test_friends_are_capped(client):
    for n in range(MAX_FRIENDS):
        friends().add("alice", f"someone-{n}")

    response = client.post(
        "/friends", json={"invite": invite_of(client, "alice")}, headers=auth("bob")
    )

    assert response.status_code == 422
    assert ("bob", "alice") not in friend_items()


def test_list_friends_with_minutes_only_for_those_sharing(client):
    befriend(client, "alice", "bob")
    befriend(client, "alice", "carol")
    put_stat("bob", "totals#this_week", {"hours": 2.5})
    put_stat("carol", "totals#this_week", {"hours": 9})
    client.patch("/me", json={"share_with_friends": False}, headers=auth("carol"))

    body = client.get("/friends", headers=auth("alice")).json()["friends"]

    assert [(f["display_name"], f["sharing"], f["minutes_this_week"]) for f in body] == [
        ("Bob", True, 150),
        ("Carol", False, None),
    ]


def test_remove_deletes_both_directions(client):
    befriend(client, "alice", "bob")

    assert client.delete("/friends/alice", headers=auth("bob")).status_code == 204
    assert friend_items() == set()
    assert client.delete("/friends/alice", headers=auth("bob")).status_code == 404


def test_removing_a_stranger_is_not_found(client):
    assert client.delete("/friends/carol", headers=auth("alice")).status_code == 404


def test_delete_me_leaves_no_friendships_pointing_at_you(client):
    befriend(client, "alice", "bob")
    befriend(client, "alice", "carol")
    befriend(client, "bob", "carol")

    assert client.delete("/me", headers=auth("alice")).status_code == 204

    assert friend_items() == {("bob", "carol"), ("carol", "bob")}
    assert client.get("/friends", headers=auth("bob")).json()["friends"][0]["user_id"] == "carol"


def test_sharing_setting(client):
    assert client.get("/me", headers=auth("alice")).json()["share_with_friends"] is True

    response = client.patch("/me", json={"share_with_friends": False}, headers=auth("alice"))

    assert response.json()["share_with_friends"] is False
    assert users().get("alice").share_with_friends is False


def test_friends_routes_need_a_session(client):
    assert client.get("/friends").status_code == 401
    assert client.get("/friends/invite").status_code == 401
    assert client.post("/friends", json={"invite": "x"}).status_code == 401


# Seeing a friend.


def artist(name, hours, image=None):
    return {
        "name": name,
        "artist_name": None,
        "streams": 9,
        "hours": hours,
        "image": image,
        "url": None,
    }


def share_some_stats(user_id):
    put_stat(user_id, "top_artists#4_weeks", [artist(f"A{n}", 20 - n) for n in range(15)])
    put_stat(
        user_id, "top_tracks#4_weeks", [{**artist(f"T{n}", 5), "track_id": "x"} for n in range(15)]
    )
    put_stat(user_id, "totals#this_week", {"streams": 300, "hours": 4.25, "artists": 9})
    put_stat(user_id, "streaks", {"current": {"days": 12}, "longest": {"days": 99}})
    put_stat(user_id, "listening_clock#4_weeks", [{"weekday": 1, "hour": 3, "minutes": 9}])


FRIEND_ROUTES = ("/friends/{}/summary", "/friends/{}/compare")


@pytest.mark.parametrize("route", FRIEND_ROUTES)
def test_strangers_and_unknown_ids_are_not_found_alike(client, route):
    share_some_stats("carol")

    stranger = client.get(route.format("carol"), headers=auth("alice"))
    nobody = client.get(route.format("no-such-user"), headers=auth("alice"))
    yourself = client.get(route.format("alice"), headers=auth("alice"))

    assert stranger.status_code == nobody.status_code == yourself.status_code == 404
    assert stranger.json() == nobody.json()


@pytest.mark.parametrize("route", FRIEND_ROUTES)
def test_a_friend_who_stops_sharing_is_not_found(client, route):
    befriend(client, "alice", "bob")
    share_some_stats("bob")
    client.patch("/me", json={"share_with_friends": False}, headers=auth("bob"))

    assert client.get(route.format("bob"), headers=auth("alice")).status_code == 404


def test_a_removed_friend_is_not_found(client):
    befriend(client, "alice", "bob")
    share_some_stats("bob")
    client.delete("/friends/bob", headers=auth("alice"))

    assert client.get("/friends/bob/summary", headers=auth("alice")).status_code == 404


def test_summary_has_only_the_agreed_fields(client):
    befriend(client, "alice", "bob")
    share_some_stats("bob")

    body = client.get("/friends/bob/summary", headers=auth("alice")).json()

    assert set(body) == {
        "user_id",
        "display_name",
        "ready",
        "top_artists",
        "top_tracks",
        "minutes_this_week",
        "streak_days",
    }
    assert len(body["top_artists"]) == len(body["top_tracks"]) == 10
    # What each row is, never how much they played it.
    assert set(body["top_artists"][0]) == {"name", "artist_name", "image", "url"}
    assert (body["ready"], body["minutes_this_week"], body["streak_days"]) == (True, 255, 12)


def test_summary_before_their_stats_are_built(client):
    befriend(client, "alice", "bob")

    body = client.get("/friends/bob/summary", headers=auth("alice")).json()

    assert body["ready"] is False
    assert (body["top_artists"], body["minutes_this_week"], body["streak_days"]) == ([], 0, 0)


def test_compare(client):
    befriend(client, "alice", "bob")
    put_stat(
        "alice", "top_artists#12_months", [artist("Nova", 10), artist("Kites", 5), artist("Old", 1)]
    )
    put_stat("alice", "top_artists#all_time", [artist("Forgotten", 50)])
    put_stat(
        "bob",
        "top_artists#12_months",
        [
            artist("kites ", 8, image="k.jpg"),
            artist("Nova", 2),
            artist("Forgotten", 1),
            artist("Fresh", 1),
        ],
    )

    body = client.get("/friends/bob/compare", headers=auth("alice")).json()

    assert 0 < body["taste_match"] < 100
    # Nova (your 1st, their 2nd) and Kites (your 2nd, their 1st) tie on worst rank; your
    # favourite goes first. "kites " matches "Kites": case and spacing don't count.
    assert [(a["your_rank"], a["their_rank"]) for a in body["both_love"]] == [(1, 2), (2, 1)]
    assert body["both_love"][1]["image"] == "k.jpg"
    # Forgotten is in your all-time list, so it isn't new to you.
    assert [a["name"] for a in body["new_to_you"]] == ["Fresh"]


def test_compare_before_stats_exist(client):
    befriend(client, "alice", "bob")

    body = client.get("/friends/bob/compare", headers=auth("alice")).json()

    assert body == {
        "user_id": "bob",
        "display_name": "Bob",
        "taste_match": None,
        "both_love": [],
        "new_to_you": [],
    }


def test_leaderboard_ranks_me_and_sharing_friends(client):
    befriend(client, "alice", "bob")
    befriend(client, "alice", "carol")
    put_stat("alice", "totals#this_week", {"hours": 1})
    put_stat("bob", "totals#this_week", {"hours": 3})
    put_stat("carol", "totals#this_week", {"hours": 9})
    client.patch("/me", json={"share_with_friends": False}, headers=auth("carol"))

    board = client.get("/friends/leaderboard", headers=auth("alice")).json()["leaderboard"]

    assert board == [
        {"rank": 1, "user_id": "bob", "display_name": "Bob", "minutes": 180, "is_you": False},
        {"rank": 2, "user_id": "alice", "display_name": "Alice", "minutes": 60, "is_you": True},
    ]


def test_leaderboard_with_no_friends_is_just_you(client):
    board = client.get("/friends/leaderboard", headers=auth("alice")).json()["leaderboard"]

    assert [(r["user_id"], r["minutes"]) for r in board] == [("alice", 0)]
