# Handoff

Where the project stands on the evening of 27 October 2026, how to run it, and what's next. For how it works,
read [architecture/README.md](architecture/README.md); for why, read
[architecture/decisions.md](architecture/decisions.md); for pictures and caching, read
[architecture/caching.md](architecture/caching.md).

## What it is

A stats.fm-style Spotify stats app, built in stages to cover cloud and data platform skills
(AWS, Terraform, Python, DuckDB; later Airflow, dbt, Iceberg, Kafka, Flink, Spark, Kubernetes).
Stage 1, the working app, is live for one user (you, Spotify display name "neimad").

## Live right now

| Piece | State |
|---|---|
| Your history | 430,966 plays in S3 (`listens/user=bt9tbr9slbgo886lyqicrn4of/…`) |
| Poller Lambda | Every 20 min, storing new plays |
| Stats Lambda | Hourly; 143 documents for you; top 100s ranked by minutes, with pictures and links |
| Catalogue cache | `catalog/spotify.json`: 422 tracks, 164 artists; Spotify paused lookups until 28 Oct 18:14 |
| API Lambda | `https://5o2g53vz3bhz4cgroqkvquvosm0dorcs.lambda-url.eu-north-1.on.aws/` |
| Web app | Local: Home, Top, Stats; real data after login, or `/?demo` |
| Tests | 116 Python tests; web lint, type-check and build in CI |

## Everything built, by PR

| PRs | What |
|---|---|
| #1 | Repo scaffold: uv workspace, ruff, pytest, pre-commit, CI, Terraform bootstrap (state bucket, budget) |
| #2 | `Listen` schema, export parser, first local DuckDB stats |
| #3 | ADR 0003: S3 is the source of truth, no listens table |
| #5–#11 | Stats engine: Parquet + dedupe, time windows, top lists, habits, behaviour, 107 documents + Wrapped, docs |
| #12 | Spotify client: OAuth, refresh, recently played; `spotify-login`, `fetch-recent` |
| #13–#14 | Terraform: S3 data bucket; DynamoDB users and stats tables |
| #17 | S3 layout, users table, history upload |
| #18 | Poller Lambda |
| #19 | Stats Lambda |
| #20 | API Lambda: Spotify login, stats endpoints |
| #21 | `scripts/deploy.py`, backend docs |
| #22 | Today / this week / this month / this year windows (143 documents) |
| #23 | `/me/now-playing`; race-safe token saving |
| #24 | `/me/recent`; stores unseen plays; forward-only cursor |
| #25–#26 | The web app; clearer "needs the latest backend" message |
| #27 | Pictures and links from Spotify's catalogue (cached in S3); rank by minutes |
| #28 | Web: real pictures, minutes first, fuller Today, logout on every tab, no Genres |
| #29 | Architecture docs, decisions, this handoff |
| #30 | Top 100; lookups #1s first; pictures for on repeat and new to you |
| #31 | Web: direct Spotify links everywhere, top 10 that expands, "minutes", aligned Today |
| #32 | Remember Spotify's back-off in the cache file |
| #33 | Web: code splitting, lazy images, home-screen manifest, accessibility, error boundaries, "updated X ago" |
| #34 | Caching docs, decisions, plan |
| #35 | Web: top navbar on desktop, animated greeting, top 10 → 50 → 100 |
| #36 | Settings (text size, animations), `DELETE /me` "delete my data", cards fade in |
| #4, #15 | Leftover test PRs, still open; safe to close |

## How to run things

```bash
# Web app (http://localhost:5173; add ?demo for made-up data)
cd web && npm install && npm run dev

# Python tests and lint
uv run pytest
uv run ruff check .

# Deploy backend changes (needs Terraform on PATH and the AWS profile)
AWS_PROFILE=spotify-stats uv run python scripts/deploy.py

# Rebuild everyone's stats now instead of waiting for the hour
AWS_PROFILE=spotify-stats aws lambda invoke --function-name spotify-stats-stats \
  --cli-binary-format raw-in-base64-out --payload '{"force": true}' out.json
```

Remember: **merged is not live**. Backend PRs need a deploy (`terraform apply`) before the app
sees them.

## Gotchas learned the hard way

- The app's built-in terminal panel can't run `uv`; use a normal terminal.
- In Git Bash, prefix AWS commands that take `/aws/...` or `/spotify-stats/...` paths with
  `MSYS_NO_PATHCONV=1`.
- Python scripts that edit files on Windows must pass `encoding="utf-8"`, or characters like
  "–" get garbled.
- Spotify's redirect URI must match exactly, with no trailing slash, and be **saved**.
- Spotify (development mode): bulk catalogue lookups return 403, genres come back empty, and
  only allow-listed users (up to 25) can log in.
- Stopping a Vite dev server before switching git branches avoids stale "file not found" errors.

## Next steps

**Before Stage 2, in this order** (agreed 2026-10-28)
1. **Concerts:** "your artists on tour" from the Ticketmaster Discovery API (free key, affiliate
   links through Impact), plus SeatGeek or Skiddle; matched to your top artists, cached daily.
   No scraping: AXS / AEG and DICE have no public API.
2. **Host the web app:** Cloudflare Pages on a new project/subdomain, API CORS for that address,
   the address added to Spotify's redirect URIs and the API's allowed redirects.
3. **Spotify quota extension:** needs the hosted site, a privacy page and delete-my-data (done).

**Soon (small)**
1. Rename the Top tab (suggested "Charts").
2. Now playing returns `fetched_at`, so the progress bar is exact through the 5-second cache.
3. Delete stat documents whose names no longer exist; close leftover PRs #4 and #15.

**Settings page** (text size and animations done in #36; still to add)
- High-contrast mode, colour themes (Spotify green, plus a few accents), time as minutes or
  hours.
- Stored in the browser first; later in the users table so it follows you to the phone app.
- Built on Tailwind theme variables, so a theme is a different set of colour tokens.

**Pictures**
- A catalogue queue: one lookup every few seconds instead of bursts, new users' top 10s first.
- On-demand lookups for a row that's missing a picture; refresh entries older than a few
  months.

**Phone app** (Expo Go, Classic Spotify + glass)
- Login, Home, Charts, Stats; reuse the API and the web app's types. Libraries:
  expo-glass-effect / expo-blur, Expo Router native tabs, Skia + victory-native charts,
  Reanimated + Moti, expo-haptics, expo-image.

**Friends (up to 25)**
- Allow-list them in the Spotify dashboard; export upload for others (upload link + importer
  Lambda); "delete my data" and a privacy page; time zone per user; host the web app (a separate
  Cloudflare Pages project or S3 + CloudFront) with CORS and the address allowed for login.
- Then battles: compare minutes, top artists and streaks with a friend.

**Data platform (the CV stages)**
- Stage 2: Airflow + dbt over the S3 data (star schema, tests), genres from Last.fm.
- Stage 3: Iceberg tables on S3, Athena, a Spark backfill.
- Stage 4: Kafka + Flink for live "today" counts.
- Stage 5: Kubernetes (kind/k3d), Prometheus + Grafana.
- Stage 6: BigQuery or Snowflake copies; Apple Music.
- Ask AWS Support to allow GitHub OIDC so merges can deploy themselves.
