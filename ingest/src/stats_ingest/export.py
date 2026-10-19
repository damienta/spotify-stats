"""Parse Spotify's Extended Streaming History export into `Listen` records.

The export is a zip (or the folder it unzips to) holding `Streaming_History_Audio_*.json` and
`Streaming_History_Video_*.json` files: JSON arrays with one object per play. Fields we don't
need, including `ip_addr` and `conn_country`, are dropped here and never stored.
"""

from __future__ import annotations

import json
import re
import zipfile
from collections import Counter
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from stats_ingest.listen import Listen, make_listen_id, track_id_from_uri

HISTORY_FILE = re.compile(r"(?:^|/)Streaming_History_(?:Audio|Video)_[^/]*\.json$")

# The raw fields that, together, identify one play.
IDENTITY_FIELDS = (
    "ts",
    "spotify_track_uri",
    "ms_played",
    "reason_start",
    "reason_end",
    "platform",
    "shuffle",
    "skipped",
    "offline",
    "offline_timestamp",
    "incognito_mode",
)


@dataclass
class ParseResult:
    listens: list[Listen] = field(default_factory=list)
    skipped: Counter[str] = field(default_factory=Counter)


def read_export(path: Path) -> Iterator[dict[str, Any]]:
    """Yield raw play records from an export zip or an unzipped export folder."""
    if path.is_file() and zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as zf:
            for name in sorted(n for n in zf.namelist() if HISTORY_FILE.search(n)):
                yield from json.loads(zf.read(name))
    elif path.is_dir():
        for file in sorted(p for p in path.rglob("*.json") if HISTORY_FILE.search(p.as_posix())):
            yield from json.loads(file.read_text(encoding="utf-8"))
    else:
        raise FileNotFoundError(f"expected a Spotify export zip or folder: {path}")


def parse_records(records: Iterable[dict[str, Any]], user_id: str) -> ParseResult:
    result = ParseResult()
    seen: set[str] = set()
    for raw in records:
        uri = raw.get("spotify_track_uri")
        if not uri:
            reason = "podcast_episode" if raw.get("spotify_episode_uri") else "no_track_metadata"
            if raw.get("audiobook_uri"):
                reason = "audiobook"
            result.skipped[reason] += 1
            continue

        listen_id = make_listen_id(user_id, {k: raw.get(k) for k in IDENTITY_FIELDS})
        if listen_id in seen:
            result.skipped["duplicate"] += 1
            continue
        seen.add(listen_id)

        result.listens.append(
            Listen(
                listen_id=listen_id,
                user_id=user_id,
                played_at=datetime.strptime(raw["ts"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC),
                track_id=track_id_from_uri(uri),
                track_name=raw["master_metadata_track_name"],
                artist_name=raw["master_metadata_album_artist_name"],
                album_name=raw["master_metadata_album_album_name"],
                source="export",
                ms_played=raw["ms_played"],
                skipped=raw.get("skipped"),
                shuffle=raw.get("shuffle"),
                platform=raw.get("platform"),
                reason_start=raw.get("reason_start"),
                reason_end=raw.get("reason_end"),
            )
        )
    return result


def parse_export(path: Path, user_id: str) -> ParseResult:
    return parse_records(read_export(path), user_id)
