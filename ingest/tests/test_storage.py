import json
from datetime import UTC, datetime

import boto3
import pytest

from stats_ingest.listen import Listen
from stats_ingest.spotify import Tokens
from stats_ingest.storage import (
    UsersTable,
    api_listens_key,
    export_listens_key,
    new_user,
    put_listens,
    raw_api_key,
    spotify_config_from_ssm,
)

AT = datetime(2026, 10, 25, 9, 30, 15, 123456, tzinfo=UTC)


def test_keys_follow_the_bucket_layout():
    assert api_listens_key("u1", AT) == "listens/user=u1/source=api/20261025T093015123456Z.jsonl"
    assert export_listens_key("u1") == "listens/user=u1/source=export/export.parquet"
    assert raw_api_key("u1", AT) == "raw/source=api/user=u1/date=2026-10-25/093015123456.json"


def test_put_listens_writes_json_lines(aws):
    s3 = boto3.client("s3")
    listen = Listen("id1", "u1", AT, "t", "Song", "Artist", "Album", "api")

    put_listens(s3, "data", "k.jsonl", [listen, listen])

    lines = s3.get_object(Bucket="data", Key="k.jsonl")["Body"].read().decode().splitlines()
    assert [json.loads(line)["listen_id"] for line in lines] == ["id1", "id1"]


def test_users_round_trip_and_updates(aws):
    users = UsersTable(boto3.resource("dynamodb").Table("users"))
    users.put(new_user("u1", "Damien", Tokens("a", "r", 1_000.5)))

    users.save_tokens("u1", Tokens("a2", "r2", 2_000.25))
    users.save_cursor("u1", 1_761_384_615_123)

    user = users.get("u1")
    assert (user.display_name, user.access_token, user.refresh_token) == ("Damien", "a2", "r2")
    assert user.expires_at == 2_000.25
    assert user.cursor_ms == 1_761_384_615_123
    assert users.get("nobody") is None


def test_all_users_are_listed(aws):
    users = UsersTable(boto3.resource("dynamodb").Table("users"))
    for n in range(3):
        users.put(new_user(f"u{n}", f"User {n}", Tokens("a", "r", 0)))

    assert sorted(u.user_id for u in users.all()) == ["u0", "u1", "u2"]


def test_spotify_config_comes_from_ssm(aws):
    ssm = boto3.client("ssm")
    for name, value in [("client_id", "id"), ("client_secret", "secret"), ("redirect_uri", "u")]:
        ssm.put_parameter(Name=f"/spotify-stats/spotify_{name}", Value=value, Type="SecureString")

    config = spotify_config_from_ssm(ssm)

    assert (config.client_id, config.client_secret, config.redirect_uri) == ("id", "secret", "u")


def test_missing_ssm_parameters_are_named(aws):
    with pytest.raises(RuntimeError, match="spotify_client_secret"):
        spotify_config_from_ssm(boto3.client("ssm"))


def test_token_saves_do_not_overwrite_newer_tokens(aws):
    users = UsersTable(boto3.resource("dynamodb").Table("users"))
    user = new_user("u1", "Damien", Tokens("a1", "r1", 100))
    users.put(user)
    poller_save, api_save = users.token_saver(user), users.token_saver(user)

    poller_save(Tokens("a2", "r2", 200))
    api_save(Tokens("a3", "r3", 300))  # refreshed from a1 too, but lost the race

    saved = users.get("u1")
    assert (saved.access_token, saved.refresh_token) == ("a2", "r2")
    assert users.save_tokens("u1", Tokens("a4", "r4", 400), replacing="a2")


def test_cursor_never_moves_back(aws):
    users = UsersTable(boto3.resource("dynamodb").Table("users"))
    users.put(new_user("u1", "Damien", Tokens("a", "r", 0)))

    users.save_cursor("u1", 200)
    users.save_cursor("u1", 100)

    assert users.get("u1").cursor_ms == 200
