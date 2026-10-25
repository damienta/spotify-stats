import json
from datetime import UTC, datetime

import boto3
import httpx

from stats_ingest.poller import poll_all, poll_user
from stats_ingest.spotify import SpotifyConfig, Tokens
from stats_ingest.storage import UsersTable, new_user

CONFIG = SpotifyConfig("id", "secret", "http://127.0.0.1:8000/callback")
NOW = datetime(2026, 10, 25, 12, 0, tzinfo=UTC)


def item(played_at, track_id="t1"):
    return {
        "played_at": played_at,
        "track": {
            "id": track_id,
            "name": "Song",
            "duration_ms": 180_000,
            "artists": [{"name": "Artist"}],
            "album": {"name": "Album"},
        },
    }


def fake_spotify(items_by_after, requests):
    def handler(request):
        requests.append(request)
        after = request.url.params.get("after")
        return httpx.Response(200, json={"items": items_by_after.get(after, []), "next": None})

    return httpx.Client(transport=httpx.MockTransport(handler))


def setup_user(cursor_ms=None):
    users = UsersTable(boto3.resource("dynamodb").Table("users"))
    user = new_user("u1", "Damien", Tokens("a", "r", expires_at=9e12))
    user.cursor_ms = cursor_ms
    users.put(user)
    return users


def keys(prefix):
    listing = boto3.client("s3").list_objects_v2(Bucket="data", Prefix=prefix)
    return [o["Key"] for o in listing.get("Contents", [])]


def test_new_plays_are_stored_and_the_cursor_moves(aws):
    users = setup_user()
    requests = []
    http = fake_spotify(
        {None: [item("2026-10-25T09:00:00Z"), item("2026-10-25T10:30:00.500Z", "t2")]}, requests
    )

    result = poll_user(
        users.get("u1"),
        http=http,
        config=CONFIG,
        users=users,
        s3=boto3.client("s3"),
        bucket="data",
        now=NOW,
    )

    assert result.new_plays == 2
    assert users.get("u1").cursor_ms == int(
        datetime(2026, 10, 25, 10, 30, 0, 500_000, tzinfo=UTC).timestamp() * 1000
    )
    [raw] = keys("raw/source=api/user=u1/")
    [listens] = keys("listens/user=u1/source=api/")
    body = boto3.client("s3").get_object(Bucket="data", Key=listens)["Body"].read().decode()
    assert [json.loads(line)["track_id"] for line in body.splitlines()] == ["t1", "t2"]
    assert raw.startswith("raw/source=api/user=u1/date=2026-10-25/")


def test_the_next_poll_asks_only_for_plays_after_the_cursor(aws):
    users = setup_user(cursor_ms=1_761_386_400_000)
    requests = []
    http = fake_spotify({}, requests)

    result = poll_user(
        users.get("u1"),
        http=http,
        config=CONFIG,
        users=users,
        s3=boto3.client("s3"),
        bucket="data",
        now=NOW,
    )

    assert result.new_plays == 0
    assert requests[0].url.params["after"] == "1761386400000"
    assert keys("listens/") == []


def test_one_failing_user_does_not_stop_the_others(aws):
    users = setup_user()
    broken = new_user("u2", "Broken", Tokens("bad", "r", expires_at=9e12))
    users.put(broken)

    def handler(request):
        if request.headers["Authorization"] == "Bearer bad":
            return httpx.Response(500, text="boom")
        return httpx.Response(200, json={"items": [item("2026-10-25T09:00:00Z")], "next": None})

    results = poll_all(
        http=httpx.Client(transport=httpx.MockTransport(handler)),
        config=CONFIG,
        users=users,
        s3=boto3.client("s3"),
        bucket="data",
    )

    assert [(r.user_id, r.new_plays) for r in results] == [("u1", 1)]
