# Bootstrap

One-off stack that creates what the other stacks depend on. Apply it by hand from your
machine with an admin AWS profile; CI never applies it.

## First run

```bash
aws sso login --profile spotify-stats
export AWS_PROFILE=spotify-stats
terraform init
terraform apply
```

This stack starts on local state because it creates the state bucket. The local
`terraform.tfstate` is git-ignored: keep it safe, or move it into the bucket once it exists
by adding a `backend "s3"` block and running `terraform init -migrate-state`.
