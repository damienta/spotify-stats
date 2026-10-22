"""The `Listen` record: one play of one track, whatever source it came from.

Every part of the system speaks this shape: the export importer and the API poller produce it,
and the stats jobs (and later the lakehouse tables and Kafka messages) consume it.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any, Literal

Source = Literal["export", "api"]


@dataclass(frozen=True, slots=True)
class Listen:
    listen_id: str
    user_id: str
    # When Spotify logged the play. For the export this is when playback stopped.
    played_at: datetime
    track_id: str
    track_name: str
    artist_name: str
    album_name: str
    source: Source
    # Only the export records these; the API leaves them as None.
    ms_played: int | None = None
    skipped: bool | None = None
    shuffle: bool | None = None
    platform: str | None = None
    reason_start: str | None = None
    reason_end: str | None = None
    # Only the API records this: the track's full length, used to estimate time listened.
    track_duration_ms: int | None = None

    def to_dict(self) -> dict[str, Any]:
        row = asdict(self)
        row["played_at"] = self.played_at.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        return row


def make_listen_id(user_id: str, identity: dict[str, Any]) -> str:
    """Deterministic ID, so importing the same play twice yields the same ID.

    `identity` holds the fields that tell one play apart from another. Several plays can share
    a timestamp (quick skips), so the timestamp alone is not enough.
    """
    payload = json.dumps({"user_id": user_id, **identity}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()[:32]


def track_id_from_uri(uri: str) -> str:
    """`spotify:track:4uLU6hMCjMI75M1A2tKUQC` -> `4uLU6hMCjMI75M1A2tKUQC`."""
    kind, _, track_id = uri.removeprefix("spotify:").partition(":")
    if kind != "track" or not track_id:
        raise ValueError(f"not a Spotify track URI: {uri!r}")
    return track_id
