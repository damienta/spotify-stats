# spotify-stats

A stats.fm-style listening tracker for Spotify, growing into a small data platform: a serverless
ingestion path on AWS, then a lakehouse (Iceberg), orchestration (Airflow + dbt) and streaming
(Kafka + Flink). Later it becomes a "battle your friends" app with Apple Music support.

See [docs/roadmap.md](docs/roadmap.md) for the stages.

## Layout

| Path | What lives there |
| --- | --- |
| `infra/bootstrap/` | One-off Terraform: remote state bucket and budget alarm |
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

## Try it on your own Spotify export

Request **Extended streaming history** from Spotify (Account → Privacy → Download your data),
unzip it into `data/` (git-ignored), then:

```bash
uv run parse-export data/my_spotify_data --user me   # export -> data/listens.jsonl
uv run convert-listens                                # dedupe -> data/listens.parquet
uv run local-stats --window 4_weeks                   # or 6_months, 12_months, all_time, year_2025
uv run local-stats --wrapped 2025                     # your own Wrapped
uv run build-stats --user me                          # every stat as JSON -> data/stats/me.json
```

## Try the live Spotify API

Create an app at developer.spotify.com (redirect URI `http://127.0.0.1:8000/callback`), put its
client ID and secret in `.env` (copy `.env.example`), then:

```bash
uv run spotify-login    # approve in the browser; the token is saved to data/ (git-ignored)
uv run fetch-recent     # your latest plays (Spotify keeps the last 50)
```

## Deploy to AWS

Everything runs serverless in `eu-north-1` (see [docs/adr](docs/adr)): a poller every 20 minutes,
a stats job every hour and an API on a Lambda function URL. Deploys run from your machine
because the account blocks GitHub OIDC:

```bash
uv run python scripts/deploy.py      # build Lambdas, plan, confirm, apply, sync secrets, check
```

First time only: apply `infra/bootstrap` (see its README), then add the printed
`spotify_redirect_uri` under Redirect URIs in the Spotify developer dashboard.
