import json
from datetime import UTC, datetime, timedelta

import boto3

from stats_jobs.job import BUILD_MARKER, compacted_key, run_user

NOW = datetime(2026, 10, 25, 12, 0, tzinfo=UTC)


def listen(n, source, played_at, ms_played=200_000):
    return {
        "listen_id": f"{source}{n}",
        "user_id": "u1",
        "played_at": played_at,
        "track_id": f"t{n}",
        "track_name": f"Song {n}",
        "artist_name": "Artist",
        "album_name": "Album",
        "source": source,
        "ms_played": ms_played if source == "export" else None,
        "track_duration_ms": None if source == "export" else 180_000,
    }


def put_jsonl(key, rows):
    body = "".join(json.dumps(r) + "\n" for r in rows)
    boto3.client("s3").put_object(Bucket="data", Key=key, Body=body.encode())


def keys(prefix="listens/"):
    listing = boto3.client("s3").list_objects_v2(Bucket="data", Prefix=prefix)
    return sorted(o["Key"] for o in listing.get("Contents", []))


def stat(name):
    item = (
        boto3.resource("dynamodb")
        .Table("stats")
        .get_item(Key={"user_id": "u1", "stat_name": name})["Item"]
    )
    return json.loads(item["data"]) if "data" in item else item


def run(workdir, now=NOW, force=False):
    workdir.mkdir(parents=True, exist_ok=True)
    return run_user(
        "u1",
        s3=boto3.client("s3"),
        bucket="data",
        stats_table=boto3.resource("dynamodb").Table("stats"),
        workdir=workdir,
        now=now,
        force=force,
    )


EXPORT = "listens/user=u1/source=export/export.jsonl"


def test_builds_documents_and_compacts_poll_files(aws, tmp_path):
    put_jsonl(EXPORT, [listen(1, "export", "2026-10-01T10:00:00Z")])
    put_jsonl("listens/user=u1/source=api/a.jsonl", [listen(2, "api", "2026-10-24T10:00:00Z")])
    put_jsonl("listens/user=u1/source=api/b.jsonl", [listen(3, "api", "2026-10-24T11:00:00Z")])

    result = run(tmp_path)

    assert result.documents > 30
    assert result.compacted == 2
    assert keys() == [compacted_key("u1"), EXPORT]
    # API plays count as heard in full (3 minutes each).
    assert stat("totals#all_time")["streams"] == 3
    assert stat("totals#all_time")["hours"] == round((200_000 + 2 * 180_000) / 3_600_000, 4)


def test_compacted_listens_are_read_back_next_time(aws, tmp_path):
    put_jsonl("listens/user=u1/source=api/a.jsonl", [listen(2, "api", "2026-10-24T10:00:00Z")])
    run(tmp_path / "1")
    put_jsonl("listens/user=u1/source=api/c.jsonl", [listen(4, "api", "2026-10-25T09:00:00Z")])

    result = run(tmp_path / "2")

    assert result.compacted == 1
    assert {t["name"] for t in stat("top_tracks#all_time")} == {"Song 2", "Song 4"}


def test_unchanged_listens_are_skipped_until_the_next_day(aws, tmp_path):
    put_jsonl(EXPORT, [listen(1, "export", "2026-10-01T10:00:00Z")])
    run(tmp_path / "1")

    assert run(tmp_path / "2").skipped
    assert not run(tmp_path / "f", force=True).skipped
    assert not run(tmp_path / "3", now=NOW + timedelta(days=1)).skipped
    assert stat(BUILD_MARKER)["built_on"] == "2026-10-26"


def test_users_without_listens_are_skipped(aws, tmp_path):
    assert run(tmp_path).skipped
