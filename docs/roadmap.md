# Roadmap

Built in stages. Each stage ends with something that works and a short write-up.
Costs stay near £0: the production path is serverless on AWS, and the heavy engines
(Kafka, Flink, Spark, Airflow, Kubernetes) run locally against the same S3 lakehouse.

## Step 0: Setup

- [ ] AWS account: MFA on root, admin login via IAM Identity Center, £1 budget alarm
- [ ] Spotify developer app (client ID/secret, redirect URI, user allow-list)
- [ ] Request Spotify data: Extended streaming history + Account data (skip technical logs)
- [x] Repo scaffold: uv, ruff, pytest, pre-commit, CI
- [ ] Terraform state bucket + GitHub OIDC so CI can run `terraform plan` on pull requests

## Stage 1: Simple stats app

- [ ] Terraform: S3 (raw), DynamoDB (users, listens, stats), SSM parameters, Lambda roles
- [ ] Spotify OAuth Lambda; refresh tokens stored encrypted
- [ ] Poller Lambda on EventBridge Scheduler (every 20 min): raw JSON to S3, deduped plays to DynamoDB
- [ ] GDPR import Lambda: S3 upload → parse → same raw format (drop `ip_addr`)
- [ ] Hourly stats Lambda with DuckDB → per-user stats in DynamoDB
- [ ] FastAPI + Mangum on a Lambda Function URL
- [ ] SwiftUI app with 3–4 stat screens

## Stage 2: Warehousing and orchestration

- [ ] Airflow (local, docker-compose)
- [ ] dbt star schema: `fct_listens`, `dim_track`, `dim_artist`, `dim_user`, SCD2 top artists
- [ ] Genre enrichment from MusicBrainz / Last.fm
- [ ] Data-quality tests that fail the DAG

## Stage 3: Lakehouse

- [ ] Iceberg on S3 with the Glue catalog, queried by Athena
- [ ] Local Spark backfill: GDPR exports + a ListenBrainz dump
- [ ] Compaction and snapshot expiry, time travel, schema evolution

## Stage 4: Streaming

- [ ] Local Kafka with Schema Registry (Avro `listen` schema)
- [ ] Flink: dedupe, enrich, write Iceberg, live counters in Redis
- [ ] Synthetic load generator; measure throughput and latency

## Stage 5: Kubernetes platform

- [ ] Local kind/k3d: ArgoCD, Strimzi, Flink and Spark operators, Airflow Helm chart
- [ ] Prometheus + Grafana: consumer lag, freshness, job failures
- [ ] Weekend EKS sprint with Terraform, then destroy

## Stage 6: Multi-engine and features

- [ ] BigQuery sandbox and Snowflake trial reading the gold data
- [ ] Battles: prompts from gold tables, live state from Flink, WebSockets
- [ ] Apple Music via MusicKit, mapped to the same `listen` schema
- [ ] TestFlight for friends
