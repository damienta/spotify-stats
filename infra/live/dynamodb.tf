# Two small tables. Listens are not stored here: they live in S3 (ADR 0003).
# Provisioned capacity keeps both inside DynamoDB's always-free 25 read and 25 write units.
# Encryption at rest uses the AWS-owned key: a customer-managed KMS key costs about $1 a month.

# One item per user: their Spotify refresh token and how far the poller has read.
resource "aws_dynamodb_table" "users" {
  name                        = "${var.project}-users"
  billing_mode                = "PROVISIONED"
  read_capacity               = 2
  write_capacity              = 2
  hash_key                    = "user_id"
  deletion_protection_enabled = true

  attribute {
    name = "user_id"
    type = "S"
  }
}

# One item per user and stat (for example top_artists#4_weeks), ready for the API to return.
resource "aws_dynamodb_table" "stats" {
  name                        = "${var.project}-stats"
  billing_mode                = "PROVISIONED"
  read_capacity               = 5
  write_capacity              = 5
  hash_key                    = "user_id"
  range_key                   = "stat_name"
  deletion_protection_enabled = true

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "stat_name"
    type = "S"
  }
}
