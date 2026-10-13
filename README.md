# spotify-stats

A stats.fm-style listening tracker for Spotify, growing into a small data platform: a serverless
ingestion path on AWS, then a lakehouse (Iceberg), orchestration (Airflow + dbt) and streaming
(Kafka + Flink). Later it becomes a "battle your friends" app with Apple Music support.

See [docs/roadmap.md](docs/roadmap.md) for the stages.

## Layout

| Path | What lives there |
| --- | --- |
| `infra/bootstrap/` | One-off Terraform: remote state bucket, budget alarm, GitHub OIDC role |
| `infra/live/` | Terraform for the app itself (S3, DynamoDB, Lambdas, scheduler) |
| `ingest/` | Python: Spotify OAuth, the recently-played poller, GDPR export import |
| `api/` | Python: FastAPI app served from Lambda |
| `jobs/` | Python: batch jobs (DuckDB stats, later Spark) |
| `ios/` | SwiftUI app |
| `docs/` | Roadmap and architecture decision records |
| `data/` | Local-only scratch data. Ignored by git: never commit Spotify exports |

## Getting started

Requires [uv](https://docs.astral.sh/uv/), Terraform >= 1.10, the AWS CLI and pre-commit.

```bash
uv sync
uv run pytest
pre-commit install
```
