output "data_bucket" {
  description = "Bucket holding uploads, raw API responses and listens."
  value       = aws_s3_bucket.data.bucket
}
