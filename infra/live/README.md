# Live

The app's infrastructure. Its state lives in the bucket created by `../bootstrap`.

```bash
export AWS_PROFILE=spotify-stats
terraform init -backend-config="bucket=$(terraform -chdir=../bootstrap output -raw state_bucket)"
terraform plan
```

CI checks formatting and validates this stack on every pull request; `plan` and `apply` run
locally (see docs/adr/0002-aws-account-constraints.md).
