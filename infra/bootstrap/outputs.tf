output "state_bucket" {
  description = "Bucket name to use in each stack's backend config."
  value       = aws_s3_bucket.tfstate.bucket
}
