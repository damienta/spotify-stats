# Bootstrap

One-off stack that creates what the other stacks depend on. Apply it by hand from your
machine with an admin AWS profile; CI never applies it.

## First run

```bash
aws sso login --profile spotify-stats
export AWS_PROFILE=spotify-stats
cp bootstrap.example.tfvars terraform.tfvars   # then set budget_email
terraform init
terraform apply
```

This stack starts on local state because it creates the state bucket. The local
`terraform.tfstate` is git-ignored: keep it safe, or move it into the bucket once it exists
by adding a `backend "s3"` block and running `terraform init -migrate-state`.

## After applying

Add two repository variables in GitHub (Settings → Secrets and variables → Actions → Variables)
from the outputs:

| Variable | Output |
| --- | --- |
| `AWS_PLAN_ROLE_ARN` | `github_plan_role_arn` |
| `TF_STATE_BUCKET` | `state_bucket` |

They aren't secrets: the role can only be assumed by this repository's workflows.
