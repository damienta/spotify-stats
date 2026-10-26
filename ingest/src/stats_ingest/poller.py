"""The poller: every 20 minutes, fetch each user's new plays and store them in S3.

Spotify only remembers someone's last 50 plays, so anything not polled in time is lost.
For each user: refresh their token if needed, ask for plays after their cursor, store the raw
response and the listens, then move the cursor to the newest play.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import boto3
import httpx

from stats_ingest.api_listens import listen_from_api, parse_played_at
from stats_ingest.spotify import SpotifyClient, SpotifyConfig
from stats_ingest.storage import (
    User,
    UsersTable,
    api_listens_key,
    env,
    put_listens,
    raw_api_key,
    spotify_config_from_ssm,
)

log = logging.getLogger()
log.setLevel(logging.INFO)


@dataclass(frozen=True)
class PollResult:
    user_id: str
    new_plays: int


def poll_user(
    user: User,
    *,
    http: httpx.Client,
    config: SpotifyConfig,
    users: UsersTable,
    s3: Any,
    bucket: str,
    now: datetime,
) -> PollResult:
    client = SpotifyClient(
        http,
        config,
        user.tokens,
        on_refresh=users.token_saver(user),
    )
    items = client.recently_played(after_ms=user.cursor_ms)
    return PollResult(
        user.user_id, store_plays(items, user, users=users, s3=s3, bucket=bucket, now=now)
    )


def store_plays(
    items: list[dict[str, Any]],
    user: User,
    *,
    users: UsersTable,
    s3: Any,
    bucket: str,
    now: datetime,
) -> int:
    """Store the recently-played items newer than the user's cursor, then move the cursor.

    Shared by the poller and the API's recently played, which stores what it fetched so stats
    stay fresh. If both store the same play, the stats job's dedupe on listen_id drops one.
    Returns how many plays were stored.
    """

    def played_ms(item: dict[str, Any]) -> int:
        return int(parse_played_at(item["played_at"]).timestamp() * 1000)

    new = [i for i in items if user.cursor_ms is None or played_ms(i) > user.cursor_ms]
    if not new:
        return 0

    # Keep exactly what Spotify returned, then the cleaned listens.
    s3.put_object(
        Bucket=bucket,
        Key=raw_api_key(user.user_id, now),
        Body=json.dumps(new).encode(),
        ContentType="application/json",
    )
    put_listens(
        s3,
        bucket,
        api_listens_key(user.user_id, now),
        [listen_from_api(item, user.user_id) for item in new],
    )
    users.save_cursor(user.user_id, max(played_ms(i) for i in new))
    return len(new)


def poll_all(
    *, http: httpx.Client, config: SpotifyConfig, users: UsersTable, s3: Any, bucket: str
) -> list[PollResult]:
    """Poll every user. One user's failure (say, a revoked token) doesn't stop the rest."""
    results = []
    for user in users.all():
        try:
            result = poll_user(
                user,
                http=http,
                config=config,
                users=users,
                s3=s3,
                bucket=bucket,
                now=datetime.now(UTC),
            )
            results.append(result)
            log.info(json.dumps({"user_id": user.user_id, "new_plays": result.new_plays}))
        except Exception:
            log.exception("polling %s failed", user.user_id)
    return results


_config: SpotifyConfig | None = None


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Lambda entry point, run on a schedule."""
    global _config
    if _config is None:  # cached across warm invocations
        _config = spotify_config_from_ssm(boto3.client("ssm"))
    users = UsersTable(boto3.resource("dynamodb").Table(env("USERS_TABLE")))
    with httpx.Client(timeout=20) as http:
        results = poll_all(
            http=http,
            config=_config,
            users=users,
            s3=boto3.client("s3"),
            bucket=env("DATA_BUCKET"),
        )
    return {"users": len(results), "new_plays": sum(r.new_plays for r in results)}
