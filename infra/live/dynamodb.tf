# Three small tables. Listens are not stored here: they live in S3 (ADR 0003).
# Provisioned capacity keeps them inside DynamoDB's always-free 25 read and 25 write units
# (2 + 20 + 2 writes, 2 + 5 + 2 reads).
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
  write_capacity              = 20 # the stats job writes ~100 documents per user at once
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

# One item per friendship direction (alice -> bob and bob -> alice), so "my friends" is one
# Query on my own partition. The API writes and deletes both items in one transaction.
# See docs/plans/friends.md.
resource "aws_dynamodb_table" "friends" {
  name                        = "${var.project}-friends"
  billing_mode                = "PROVISIONED"
  read_capacity               = 2
  write_capacity              = 2
  hash_key                    = "user_id"
  range_key                   = "friend_id"
  deletion_protection_enabled = true

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "friend_id"
    type = "S"
  }
}
