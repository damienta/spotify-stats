"""Where data lives in AWS, and the users table.

S3 data bucket layout (see infra/live/s3.tf):
    uploads/user=<id>/...                         Spotify export zips (expire after 7 days)
    raw/source=api/user=<id>/date=<day>/<t>.json   recently-played responses, untouched
    listens/user=<id>/source=export/export.parquet the user's export, cleaned
    listens/user=<id>/source=api/<t>.jsonl         listens from each poll
    listens/user=<id>/source=api/compacted.parquet poll files merged by the stats job
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from stats_ingest.listen import Listen
from stats_ingest.spotify import SpotifyConfig, Tokens

SSM_PREFIX = "/spotify-stats"


def listens_prefix(user_id: str) -> str:
    return f"listens/user={user_id}/"


def api_listens_key(user_id: str, fetched_at: datetime) -> str:
    return f"{listens_prefix(user_id)}source=api/{fetched_at:%Y%m%dT%H%M%S%fZ}.jsonl"


def export_listens_key(user_id: str) -> str:
    return f"{listens_prefix(user_id)}source=export/export.parquet"


def artist_stat_name(name: str) -> str:
    """The stats item holding one artist's page, for example `artist#3f2a...`.

    Hashed so any name (spaces, accents, emoji) makes a short, safe key; case-folded so the
    app finds the page however the name is capitalised.
    """
    return f"artist#{hashlib.sha256(name.casefold().encode()).hexdigest()[:16]}"


def user_prefixes(user_id: str) -> list[str]:
    """Every S3 prefix holding one user's data; deleting an account empties all of them."""
    return [
        f"uploads/user={user_id}/",
        f"raw/source=api/user={user_id}/",
        listens_prefix(user_id),
    ]


def delete_prefix(s3: Any, bucket: str, prefix: str) -> int:
    """Delete every object under a prefix, 1000 per request. Returns how many went."""
    deleted = 0
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=prefix):
        keys = [{"Key": o["Key"]} for o in page.get("Contents", [])]
        if keys:
            s3.delete_objects(Bucket=bucket, Delete={"Objects": keys, "Quiet": True})
            deleted += len(keys)
    return deleted


def raw_api_key(user_id: str, fetched_at: datetime) -> str:
    return f"raw/source=api/user={user_id}/date={fetched_at:%Y-%m-%d}/{fetched_at:%H%M%S%f}.json"


def put_listens(s3: Any, bucket: str, key: str, listens: Iterable[Listen]) -> None:
    body = "".join(json.dumps(li.to_dict()) + "\n" for li in listens)
    s3.put_object(Bucket=bucket, Key=key, Body=body.encode(), ContentType="application/x-ndjson")


@dataclass
class User:
    user_id: str
    display_name: str
    refresh_token: str
    access_token: str
    expires_at: float
    created_at: str
    # Unix ms of the newest play already stored; the poller asks Spotify for anything after it.
    cursor_ms: int | None = None

    @property
    def tokens(self) -> Tokens:
        return Tokens(self.access_token, self.refresh_token, self.expires_at)

    def with_tokens(self, tokens: Tokens) -> User:
        return User(**{**asdict(self), **tokens.to_dict()})


class UsersTable:
    """The DynamoDB users table: one item per user."""

    def __init__(self, table: Any) -> None:
        self.table = table

    def get(self, user_id: str) -> User | None:
        item = self.table.get_item(Key={"user_id": user_id}).get("Item")
        return _user_from_item(item) if item else None

    def put(self, user: User) -> None:
        item = {k: v for k, v in asdict(user).items() if v is not None}
        item["expires_at"] = Decimal(str(user.expires_at))
        self.table.put_item(Item=item)

    def delete(self, user_id: str) -> None:
        self.table.delete_item(Key={"user_id": user_id})

    def all(self) -> list[User]:
        items, kwargs = [], {}
        while True:
            page = self.table.scan(**kwargs)
            items.extend(page["Items"])
            if "LastEvaluatedKey" not in page:
                return [_user_from_item(i) for i in items]
            kwargs["ExclusiveStartKey"] = page["LastEvaluatedKey"]

    def save_tokens(self, user_id: str, tokens: Tokens, replacing: str | None = None) -> bool:
        """Store refreshed tokens. With `replacing` (the access token they were refreshed from),
        only if nobody else saved newer ones meanwhile: the poller and the API both refresh, and
        the slower one mustn't overwrite fresh tokens with stale ones. Returns whether it saved.
        """
        condition = {}
        values: dict[str, Any] = {
            ":a": tokens.access_token,
            ":r": tokens.refresh_token,
            ":e": Decimal(str(tokens.expires_at)),
        }
        if replacing is not None:
            condition = {"ConditionExpression": "access_token = :old"}
            values[":old"] = replacing
        try:
            self.table.update_item(
                Key={"user_id": user_id},
                UpdateExpression="SET access_token = :a, refresh_token = :r, expires_at = :e",
                ExpressionAttributeValues=values,
                **condition,
            )
        except self.table.meta.client.exceptions.ConditionalCheckFailedException:
            return False
        return True

    def token_saver(self, user: User) -> Callable[[Tokens], None]:
        """An `on_refresh` callback for SpotifyClient that saves tokens without races."""
        current = [user.access_token]

        def save(tokens: Tokens) -> None:
            self.save_tokens(user.user_id, tokens, replacing=current[0])
            current[0] = tokens.access_token

        return save

    def save_cursor(self, user_id: str, cursor_ms: int) -> None:
        """Move the cursor forward. It never moves back, even when the poller and the API
        store plays at the same time."""
        already_newer = self.table.meta.client.exceptions.ConditionalCheckFailedException
        with contextlib.suppress(already_newer):
            self.table.update_item(
                Key={"user_id": user_id},
                UpdateExpression="SET cursor_ms = :c",
                ConditionExpression="attribute_not_exists(cursor_ms) OR cursor_ms < :c",
                ExpressionAttributeValues={":c": cursor_ms},
            )


def _user_from_item(item: dict[str, Any]) -> User:
    return User(
        user_id=item["user_id"],
        display_name=item.get("display_name", ""),
        refresh_token=item["refresh_token"],
        access_token=item.get("access_token", ""),
        expires_at=float(item.get("expires_at", 0)),
        created_at=item.get("created_at", ""),
        cursor_ms=int(item["cursor_ms"]) if item.get("cursor_ms") is not None else None,
    )


def new_user(user_id: str, display_name: str, tokens: Tokens) -> User:
    return User(
        user_id=user_id,
        display_name=display_name,
        created_at=datetime.now(UTC).isoformat(timespec="seconds"),
        **tokens.to_dict(),
    )


def spotify_config_from_ssm(ssm: Any, prefix: str = SSM_PREFIX) -> SpotifyConfig:
    """Read the Spotify app credentials from SSM Parameter Store."""
    names = [f"{prefix}/spotify_client_id", f"{prefix}/spotify_client_secret"]
    names.append(f"{prefix}/spotify_redirect_uri")
    response = ssm.get_parameters(Names=names, WithDecryption=True)
    values = {p["Name"].rsplit("/", 1)[1]: p["Value"] for p in response["Parameters"]}
    missing = {n.rsplit("/", 1)[1] for n in names} - values.keys()
    if missing:
        raise RuntimeError(f"missing SSM parameters: {sorted(missing)}")
    return SpotifyConfig(
        values["spotify_client_id"],
        values["spotify_client_secret"],
        values["spotify_redirect_uri"],
    )


def data_bucket_name(account_id: str) -> str:
    return f"spotify-stats-data-{account_id}"


USERS_TABLE = "spotify-stats-users"
STATS_TABLE = "spotify-stats-stats"


def env(name: str) -> str:
    """A required Lambda environment variable."""
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"environment variable {name} is not set")
    return value
