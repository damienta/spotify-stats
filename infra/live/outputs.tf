output "data_bucket" {
  description = "Bucket holding uploads, raw API responses and listens."
  value       = aws_s3_bucket.data.bucket
}

output "users_table" {
  description = "DynamoDB table of users, tokens and poll cursors."
  value       = aws_dynamodb_table.users.name
}

output "stats_table" {
  description = "DynamoDB table of precomputed stats documents."
  value       = aws_dynamodb_table.stats.name
}
