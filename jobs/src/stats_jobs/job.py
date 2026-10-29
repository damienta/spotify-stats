"""The hourly stats job: rebuild each user's stat documents from their listens in S3.

For each user it downloads every listens file, builds the documents (stats_jobs.documents),
adds pictures and links to the top lists (stats_jobs.catalog), writes them to the DynamoDB
stats table, then compacts the poller's small JSON Lines files
into one Parquet file. Users whose listens haven't changed are skipped, except that everyone is
rebuilt once a day because rolling windows ("4 weeks") move even without new plays.

Every user's `concerts` document (stats_jobs.concerts) is rewritten each run from their top
artists, so it stays current even when their stats are skipped.
"""

from __future__ import annotations

import json
import logging
import tempfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import boto3
import httpx
from botocore.config import Config

from stats_ingest.storage import (
    SSM_PREFIX,
    UsersTable,
    env,
    listens_prefix,
    spotify_config_from_ssm,
)
from stats_jobs.catalog import Catalog, enrich, spotify_fetch
from stats_jobs.concerts import (
    SSM_KEY_NAME,
    Concerts,
    concerts_document,
    favourite_artists,
    ticketmaster_fetch,
)
from stats_jobs.documents import build_documents
from stats_jobs.stats import connect
from stats_jobs.windows import LOCAL_TZ

log = logging.getLogger()
log.setLevel(logging.INFO)

# The stats item recording what the last build was made from.
BUILD_MARKER = "_build"


@dataclass(frozen=True)
class JobResult:
    user_id: str
    documents: int
    compacted: int
    skipped: bool = False
    pictured: int = 0


def list_listens(s3: Any, bucket: str, user_id: str) -> list[dict[str, Any]]:
    objects: list[dict[str, Any]] = []
    kwargs = {"Bucket": bucket, "Prefix": listens_prefix(user_id)}
    while True:
        page = s3.list_objects_v2(**kwargs)
        objects.extend(page.get("Contents", []))
        if not page.get("IsTruncated"):
            return objects
        kwargs["ContinuationToken"] = page["NextContinuationToken"]


def compacted_key(user_id: str) -> str:
    return f"{listens_prefix(user_id)}source=api/compacted.parquet"


def build_marker(objects: list[dict[str, Any]]) -> str:
    """Changes whenever a listens file is added, replaced or removed."""
    return f"{len(objects)}:{max(o['LastModified'] for o in objects).isoformat()}"


def run_user(
    user_id: str,
    *,
    s3: Any,
    bucket: str,
    stats_table: Any,
    workdir: Path,
    now: datetime,
    force: bool = False,
    catalog: Catalog | None = None,
) -> JobResult:
    objects = list_listens(s3, bucket, user_id)
    if not objects:
        return JobResult(user_id, 0, 0, skipped=True)

    marker = build_marker(objects)
    key = {"user_id": user_id, "stat_name": BUILD_MARKER}
    previous = stats_table.get_item(Key=key).get("Item", {})
    unchanged = previous.get("marker") == marker
    # "Today" and the other windows move at midnight on the listener's clock.
    today = now.astimezone(LOCAL_TZ).date().isoformat()
    if unchanged and previous.get("built_on") == today and not force:
        return JobResult(user_id, 0, 0, skipped=True)

    paths = []
    for n, obj in enumerate(objects):
        path = workdir / f"{n}{Path(obj['Key']).suffix}"
        s3.download_file(bucket, obj["Key"], str(path))
        paths.append(path)
    con = connect(paths, materialize=True)

    documents = build_documents(con, user_id, now)
    pictured = enrich(documents, catalog) if catalog else 0
    with stats_table.batch_writer() as batch:
        for doc in documents.values():
            batch.put_item(
                Item={
                    "user_id": user_id,
                    "stat_name": doc["stat_name"],
                    "generated_at": doc["generated_at"],
                    "data": json.dumps(doc["data"], ensure_ascii=False),
                }
            )

    # Merge every poll file into one Parquet, then delete only the files that were merged:
    # a poll that lands meanwhile is picked up next run.
    api_prefix = f"{listens_prefix(user_id)}source=api/"
    poll_files = [
        o["Key"] for o in objects if o["Key"].startswith(api_prefix) and o["Key"].endswith(".jsonl")
    ]
    if poll_files:
        compacted = workdir / "compacted.parquet"
        con.sql(
            "SELECT * EXCLUDE (played_at_local) FROM listens WHERE source = 'api' "
            "ORDER BY played_at"
        ).write_parquet(str(compacted), compression="zstd")
        s3.upload_file(str(compacted), bucket, compacted_key(user_id))
        for start in range(0, len(poll_files), 1000):
            batch_keys = poll_files[start : start + 1000]
            s3.delete_objects(Bucket=bucket, Delete={"Objects": [{"Key": k} for k in batch_keys]})
        marker = build_marker(list_listens(s3, bucket, user_id))

    stats_table.put_item(
        Item={
            **key,
            "marker": marker,
            "built_on": today,
            "generated_at": now.isoformat(),
        }
    )
    return JobResult(user_id, len(documents), len(poll_files), pictured=pictured)


# Recent favourites and long-time ones both count for "your artists on tour".
CONCERT_LISTS = ("top_artists#4_weeks", "top_artists#12_months")


def write_concerts(user_id: str, *, stats_table: Any, concerts: Concerts, now: datetime) -> int:
    """Rewrite the user's `concerts` document. Returns how many artists have dates."""
    lists = []
    for name in CONCERT_LISTS:
        item = stats_table.get_item(Key={"user_id": user_id, "stat_name": name}).get("Item")
        if item:
            lists.append(json.loads(item["data"]))
    today = now.astimezone(LOCAL_TZ).date()
    data = concerts_document(favourite_artists(lists), concerts, today)
    stats_table.put_item(
        Item={
            "user_id": user_id,
            "stat_name": "concerts",
            "generated_at": now.isoformat(),
            "data": json.dumps(data, ensure_ascii=False),
        }
    )
    return len(data)


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Lambda entry point, run hourly.

    `{"user_ids": [...]}` limits it to some users; `{"force": true}` rebuilds even unchanged
    listens, for example after a change to how stats are calculated.
    """
    # Writing ~100 documents per user can briefly exceed the table's provisioned capacity.
    retries = Config(retries={"mode": "adaptive", "max_attempts": 10})
    dynamodb = boto3.resource("dynamodb", config=retries)
    s3 = boto3.client("s3")
    stats_table = dynamodb.Table(env("STATS_TABLE"))
    user_ids = event.get("user_ids") or [
        u.user_id for u in UsersTable(dynamodb.Table(env("USERS_TABLE"))).all()
    ]
    bucket = env("DATA_BUCKET")
    http = httpx.Client(timeout=10)
    try:
        catalog = Catalog.load(s3, bucket, spotify_fetch(http, spotify_config_from_ssm(ssm())))
    except Exception:
        # Stats without pictures beat no stats.
        log.exception("the Spotify catalogue is unavailable; building stats without pictures")
        catalog = None

    try:
        api_key = ssm().get_parameter(Name=f"{SSM_PREFIX}/{SSM_KEY_NAME}", WithDecryption=True)[
            "Parameter"
        ]["Value"]
        concerts = Concerts.load(s3, bucket, ticketmaster_fetch(http, api_key))
    except Exception:
        log.exception("Ticketmaster is unavailable; skipping concerts")
        concerts = None

    results = []
    for user_id in user_ids:
        try:
            with tempfile.TemporaryDirectory() as workdir:
                result = run_user(
                    user_id,
                    s3=s3,
                    bucket=bucket,
                    stats_table=stats_table,
                    workdir=Path(workdir),
                    now=datetime.now(UTC),
                    force=bool(event.get("force")),
                    catalog=catalog,
                )
            results.append(result)
            log.info(json.dumps(asdict(result)))
        except Exception:
            log.exception("stats for %s failed", user_id)
        if concerts:
            try:
                touring = write_concerts(
                    user_id, stats_table=stats_table, concerts=concerts, now=datetime.now(UTC)
                )
                log.info(json.dumps({"user_id": user_id, "artists_touring": touring}))
            except Exception:
                log.exception("concerts for %s failed", user_id)
    if catalog:
        catalog.save(s3, bucket)
        log.info(json.dumps({"catalog_lookups": catalog.lookups}))
    if concerts:
        concerts.save(s3, bucket)
        log.info(json.dumps({"ticketmaster_calls": concerts.calls}))
    http.close()
    return {"users": len(results), "built": sum(not r.skipped for r in results)}


def ssm() -> Any:
    return boto3.client("ssm")
