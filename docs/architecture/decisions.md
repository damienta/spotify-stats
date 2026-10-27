# Decisions so far

Every significant choice, with the reason and what it cost. Grouped by area, roughly in the
order they were made. ADRs 0001–0003 in [../adr](../adr) are the formal versions of the first
few.

## Platform and cost

| Decision | Why | Trade-off |
|---|---|---|
| **AWS**, not Oracle Cloud's free VM | AWS is what data platform jobs ask for; serverless pieces stay free at this size | Some free tiers are time-limited, so spend controls matter |
| **Nothing always-on**: Lambda + S3 + DynamoDB (ADR 0001) | A personal app is idle 99% of the time; paying only per request keeps it near £0 | Cold starts; heavy engines can't run in AWS for free |
| **Heavy engines run locally** (Kafka, Flink, Spark, Airflow, Kubernetes, later stages) | Your PC is strong and free; they read and write the same S3 data | They aren't "production", which the write-ups say honestly |
| **eu-north-1 only** (ADR 0002) | The account's managed policy denies every other region | Slightly fewer services than eu-west-2 |
| **IAM user for your PC** instead of `aws login` | `aws login` doesn't support this account type | A long-lived key on your PC; it's scoped and kept in `~/.aws` |
| **No GitHub OIDC; deploy from your PC** (ADR 0002) | The account's policy denies creating OIDC providers | No automatic deploys; merged ≠ live until `apply` |
| **$1 budget alarm and a spend limit** | Catch mistakes on day one | None |

## Repository and workflow

| Decision | Why |
|---|---|
| **One repo, uv workspace**: `ingest`, `jobs`, `api` packages, plus `web/` and `infra/` | Shared `Listen` schema and Spotify client; each Lambda ships only what it needs |
| **Small PRs; Terraform in separate commits** | Easy to review; infra changes stand out because they need an `apply` |
| **ruff, pytest, pre-commit (gitleaks, terraform fmt), CI** | Catch style, bugs and leaked secrets before they land |
| **Tests never use your real export** | Personal data stays out of git; fixtures are fake |
| **Terraform state in its own S3 bucket with locking** (`infra/bootstrap`) | Safe, shared state; the bootstrap stack is tiny and rarely changes |

## Data model

| Decision | Why |
|---|---|
| **One `Listen` schema for every source** | Export and API plays flow through the same code; Apple Music can map to it later |
| **`listen_id` is a fingerprint (sha256) of a play's identifying fields** | `(user, played_at)` isn't unique: about 42k plays share a second with another (quick skips) |
| **Drop IP address and country** | Not needed; less personal data stored |
| **Stream = at least 30 s; skip = under 30 s** | Matches Spotify's own counting; Spotify's `skipped` flag is always false before 2022, so it can't be used |
| **API plays count as heard in full** (`coalesce(ms_played, track_duration_ms)`) | The API doesn't say how long you listened |
| **London time for days, hours and years** (`played_at_local`) | Matches how you think about "today"; one fixed zone until users have their own |
| **Rank lists by time played, then streams** | Lots of skipped plays shouldn't beat fewer full listens |
| **Tracks grouped by name + artist, not track ID** | The single and the album version of a song count as one |

## Storage

| Decision | Why | Trade-off |
|---|---|---|
| **S3 is the source of truth for plays; no DynamoDB listens table** (ADR 0003) | Cheap for millions of rows; DuckDB reads it fast; DynamoDB per-play writes would cost more and add nothing | Duplicates can exist in storage, so every reader must dedupe on `listen_id` |
| **Dedupe when reading, not when writing** | Writers stay simple and can retry safely; the export row wins over the API's | Reads do a little more work |
| **Parquet (zstd) for history** | 171 MB of JSON → 13 MB; columnar, so queries read only the columns they need | Not human-readable |
| **Poll files as small JSON Lines, compacted hourly** | Each poll writes a tiny file safely; the stats job merges them so S3 doesn't fill with thousands of small files | One more step in the job; it only ever deletes files it merged |
| **Raw API responses kept, untouched** | Can reprocess if parsing changes | A little storage |
| **DynamoDB for finished stats and users** | Millisecond lookups by key; the app reads one document, never computes | Each item is capped at 400 KB, so long lists are trimmed (top 50, monthly grain for long windows) |
| **Provisioned DynamoDB capacity inside the free tier** | Free | Bursts get throttled, so writes use adaptive retries |
| **No customer-managed KMS key** | About $1 a month; default encryption at rest is enough here | Less control over keys |
| **Uploads expire after 7 days** | Export zips are only needed until imported | None |

## Ingestion

| Decision | Why |
|---|---|
| **Poll every 20 minutes** | Spotify keeps only your last 50 plays; songs average about 3 minutes, so 20 minutes is well inside 50 |
| **A cursor per user (`cursor_ms`)** | Ask Spotify only for plays newer than the last stored one; the cursor only ever moves forward |
| **Export upload is a one-off backfill; login starts live collection** | The API has no history beyond 50 plays; the export is the only way to get the past |
| **Only read scopes** (`user-read-recently-played`, `user-read-currently-playing`) | The app can see what you play and nothing else |
| **Refreshed tokens saved with a conditional write** | The poller and the API both refresh; the slower one mustn't overwrite newer tokens |
| **Opening the app stores unseen plays** (`/me/recent`) | Fresher stats for free, using code shared with the poller |

## Stats

| Decision | Why |
|---|---|
| **Precompute everything hourly; serve finished documents** | Opening the app is instant and costs one DynamoDB read; Spotify is never hit for stats |
| **DuckDB inside Lambda, in memory** | Fast SQL over Parquet with no server; your whole history fits in 1.5 GB |
| **One query function per stat, run per window with `$start` and `$end`** | 11 functions instead of 143 near-identical queries |
| **Rebuild all documents for a user, overwrite in place** | About 3 s per user; simpler and safer than working out what changed |
| **Skip users with no new files, except once a day** | Saves work; the daily run keeps rolling windows correct |
| **Deterministic ordering everywhere** (integer milliseconds and name tiebreaks) | The same data always gives the same documents, which tests rely on |
| **Calendar windows (today, this week/month/year) alongside rolling ones** | The app's Day / Week / Month / Year switcher |

## Pictures and links

| Decision | Why | Trade-off |
|---|---|---|
| **Look up pictures in the stats job, not when the app opens** | One lookup per item, ever; the app stays fast | New items get pictures within an hour or so |
| **Store Spotify's image URLs, not the images** | Spotify wants its artwork shown from its servers | URLs could change; the cache can be refreshed |
| **App credentials (client credentials) for lookups** | Works for every user without spending anyone's login | None |
| **One shared cache file in S3** (`catalog/spotify.json`) | Free, one read and one write per run, shared by all users | Fine while one job writes it at a time |
| **One-at-a-time lookups, 300 per run** | Spotify returns 403 for bulk lookups to development-mode apps | A first run takes a few hours to picture everything |
| **No genres** | Spotify returns no genres to this app any more | A Genres tab needs another source (Last.fm or MusicBrainz) |

## API and login

| Decision | Why |
|---|---|
| **FastAPI on Lambda through Mangum, on a function URL** | A normal Python web app, no API Gateway to pay for or configure |
| **Spotify login through the API; the app never sees Spotify tokens** | Refresh tokens stay server-side |
| **Our own HMAC-signed session tokens (30 days), and signed OAuth `state` (10 min)** | No session table; `state` stops forged logins and carries the app's return address |
| **Only app addresses allowed as `redirect_uri`** | Stops the login being used to send tokens to someone else's site |
| **Secrets in SSM, filled after Terraform** | Keeps secrets out of Terraform state |
| **Public function URL limited to invocations through the URL** | Nobody can call the Lambda directly from another AWS account |
| **Now playing cached 5 s per user** | The app polls; this keeps Spotify calls low |

## Web app

| Decision | Why |
|---|---|
| **Web app first, then an Expo Go phone app** | No Mac and no $99 Apple programme needed for either; the web app reuses the portfolio's libraries |
| **Runs locally only** | Not putting personal data online; no hosting or domain needed |
| **Vite dev proxy for `/api`** | Same origin, so the API needs no CORS setup while it's local |
| **Classic Spotify colours, glass cards** | Your pick (P1 + S4) |
| **React Bits, Skiper UI, shadcn/ui, Framer Motion** | Same look and components as the portfolio |
| **TanStack Query for data** | Caching across tabs, polling for now playing, sensible retries |
| **Minutes first, hours in brackets** | Easier to compare; your preference |
| **Demo mode (`?demo`)** | Test and screenshot without logging in or showing real data |

## Things deliberately left for later

- Other people uploading exports (needs an upload link and an importer Lambda).
- Each user's own time zone.
- Hosting the web app, CORS, and a privacy page with "delete my data".
- More than 25 users: Spotify's development mode limit.
- Automatic deploys, once the AWS account allows GitHub OIDC.
