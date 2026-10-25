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
        on_refresh=lambda tokens: users.save_tokens(user.user_id, tokens),
    )
    items = client.recently_played(after_ms=user.cursor_ms)
    if not items:
        return PollResult(user.user_id, 0)

    # Keep exactly what Spotify returned, then the cleaned listens.
    s3.put_object(
        Bucket=bucket,
        Key=raw_api_key(user.user_id, now),
        Body=json.dumps(items).encode(),
        ContentType="application/json",
    )
    put_listens(
        s3,
        bucket,
        api_listens_key(user.user_id, now),
        [listen_from_api(item, user.user_id) for item in items],
    )
    newest = max(parse_played_at(item["played_at"]) for item in items)
    users.save_cursor(user.user_id, int(newest.timestamp() * 1000))
    return PollResult(user.user_id, len(items))


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
