# 1. Serverless on AWS, heavy engines run locally

Date: 2026-10-13
Status: Accepted

## Context

The project should cost close to nothing to run, but still use the tools a data platform
team uses: Kafka, Flink, Spark, Airflow, Iceberg and Kubernetes. Running those as managed
services (MSK, EMR, MWAA, EKS) 24/7 would cost hundreds of pounds a month.

Only two things must happen while nobody is at a keyboard: polling Spotify's
recently-played endpoint (it returns at most 50 tracks, so plays are lost if it isn't polled
often enough) and answering API requests from the app.

## Decision

- The always-needed path is serverless: EventBridge Scheduler → Lambda poller → S3 (raw)
  and DynamoDB, plus a Lambda-hosted API. Secrets live in SSM Parameter Store.
- Raw data lands in S3 from day one, so it becomes the bronze layer of the lakehouse later.
- Kafka, Flink, Spark, Airflow and Kubernetes run locally in Docker against the same S3
  bucket and Glue catalog. Managed equivalents are used only in short, torn-down sprints.

## Consequences

- Running cost stays within AWS's always-free limits plus pennies of S3 and Athena.
- There is no always-on streaming demo; streaming is shown with recordings and write-ups.
- Experience with managed services at scale (MSK, EMR, MWAA, EKS) is deliberately left out.
  Open formats (Iceberg, the S3 API, Kafka) keep the design portable to them.
