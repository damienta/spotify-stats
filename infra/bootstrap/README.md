# Bootstrap

One-off stack that creates what the other stacks depend on: the Terraform state bucket and
the monthly budget alarm. Apply it by hand from your
machine with an admin AWS profile; CI never applies it.

## First run

This account only allows **eu-north-1** (an AWS-managed region restriction), so every stack uses it.
The stack creates its own state bucket, so the first apply runs on local state and then moves
the state into the bucket:

```bash
export AWS_PROFILE=spotify-stats
cp bootstrap.example.tfvars terraform.tfvars   # then set budget_email
mv backend.tf backend.tf.off && terraform init && terraform apply
mv backend.tf.off backend.tf
terraform init -migrate-state -backend-config="bucket=$(terraform output -raw state_bucket)"
```

Later runs only need `terraform init -backend-config="bucket=spotify-stats-tfstate-<account id>"`.
