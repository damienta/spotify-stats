"""Turn Spotify Web API recently-played items into `Listen` records."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from stats_ingest.listen import Listen, make_listen_id


def parse_played_at(value: str) -> datetime:
    """`2026-10-22T09:15:31.123Z` (milliseconds are sometimes missing) to an aware datetime."""
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def listen_from_api(item: dict[str, Any], user_id: str) -> Listen:
    track = item["track"]
    played_at = parse_played_at(item["played_at"])
    return Listen(
        listen_id=make_listen_id(
            user_id, {"api_played_at": item["played_at"], "track_id": track["id"]}
        ),
        user_id=user_id,
        played_at=played_at,
        track_id=track["id"],
        track_name=track["name"],
        artist_name=track["artists"][0]["name"],
        album_name=track["album"]["name"],
        source="api",
        # The API doesn't say how long was listened, only how long the track is.
        track_duration_ms=track.get("duration_ms"),
    )
