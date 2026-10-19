# 3. S3 is the source of truth for listens

Date: 2026-10-20
Status: Accepted

## Context

The first design wrote every play twice: to S3, and to a DynamoDB `listens` table whose
conditional writes rejected duplicates. Every listen now carries a deterministic `listen_id`
(a fingerprint of the fields that identify a play), so the same play always gets the same ID
however many times it is ingested.

## Decision

- Listens are stored only in S3. There is no DynamoDB `listens` table.
- Duplicates are allowed to land in S3 and are removed when read: the stats job keeps one row
  per `listen_id`.
- DynamoDB keeps two small tables: `users` (tokens, poll cursor) and `stats` (precomputed
  answers for the API).

## Consequences

- One copy of the data, one place to back up, and a cheaper write path.
- DynamoDB stays within the always-free tier: it never holds per-play rows.
- Every consumer must dedupe on `listen_id`. In Stage 3 that moves into Iceberg `MERGE`
  statements, so the tables themselves stay duplicate-free.
