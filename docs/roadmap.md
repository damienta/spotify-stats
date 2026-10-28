# Roadmap

Built in stages. Each stage ends with something that works and a short write-up.
Costs stay near £0: the production path is serverless on AWS, and the heavy engines
(Kafka, Flink, Spark, Airflow, Kubernetes) run locally against the same S3 lakehouse.

## Step 0: Setup

- [x] AWS account: upgraded project with a spend limit, early cost controls and a $1 budget alarm
- [x] Spotify developer app (client ID/secret, redirect URI, user allow-list)
- [x] Request Spotify data: Extended streaming history + Account data (skip technical logs)
- [x] Repo scaffold: uv, ruff, pytest, pre-commit, CI
- [x] Terraform state bucket and budget alarm (GitHub OIDC is blocked by the account; see ADR 0002)

## Stage 1: Simple stats app

- [x] `Listen` schema and export parser (`parse-export`)
- [x] Stats job, run locally: Parquet, dedupe, time windows on London time, top lists, habits, skips, discoveries, Wrapped (`build-stats`, `local-stats`)
- [x] Spotify client: OAuth, token refresh, recently played, `spotify-login` and `fetch-recent`
- [x] Terraform: S3 data bucket, DynamoDB (users, stats), SSM parameters, Lambda roles
- [x] Spotify login through the API; refresh tokens in DynamoDB (encrypted at rest)
- [x] Poller Lambda every 20 min: raw JSON and listens to S3
- [x] Export upload from the CLI (`upload-export`); an import Lambda for other users comes later
- [x] Hourly stats Lambda with DuckDB (dedupes on listen_id, compacts poll files) → DynamoDB
- [x] FastAPI + Mangum on a Lambda function URL, one-command deploy (`scripts/deploy.py`)
- [x] Today / this week / this month / this year; live now playing and recently played
- [x] Pictures and links from Spotify's catalogue; lists ranked by minutes
- [x] Web app (local): login, Home, Top, Stats; demo mode
- [x] Top 100 with expand, direct Spotify links everywhere, remembered Spotify back-off
- [x] Web: code splitting, lazy images, home-screen manifest, accessibility, error boundaries
- [ ] Rename the Top tab (suggested: Charts)
- [x] Top navbar, top 10 → 50 → 100, Settings (text size, animations), delete my data
- [ ] Concerts: your top artists' upcoming gigs (Ticketmaster Discovery API + affiliate links)
- [ ] Host the web app (Cloudflare Pages) and request Spotify's quota extension
- [ ] Settings, more: high contrast, colour themes, minutes vs hours
- [ ] Catalogue queue: a steady trickle of lookups instead of bursts; new users first
- [ ] Mobile app (Expo / React Native, runs in Expo Go): login, Home, Top, Stats

## Stage 2: Warehousing and orchestration

- [ ] Airflow (local, docker-compose)
- [ ] dbt star schema: `fct_listens`, `dim_track`, `dim_artist`, `dim_user`, SCD2 top artists
- [ ] Genre enrichment from MusicBrainz / Last.fm (Spotify no longer returns genres)
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
