output "state_bucket" {
  description = "Bucket name to use in each stack's backend config."
  value       = aws_s3_bucket.tfstate.bucket
}

output "github_plan_role_arn" {
  description = "Set as the AWS_PLAN_ROLE_ARN repository variable in GitHub."
  value       = aws_iam_role.github_plan.arn
}
