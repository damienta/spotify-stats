# Bootstrap

One-off stack that creates what the other stacks depend on. Apply it by hand from your
machine with an admin AWS profile; CI never applies it.

## First run

This account only lets your console identity use AWS services, so apply from **AWS CloudShell**
(bottom-left of the console):

```bash
curl -fsSL https://raw.githubusercontent.com/damienta/spotify-stats/main/scripts/cloudshell-bootstrap.sh | BUDGET_EMAIL=you@example.com bash
```

The script installs Terraform, applies this stack on local state, then moves the state into the
bucket it just created. Re-running it is safe: later runs use the remote state directly.

## After applying

Add two repository variables in GitHub (Settings → Secrets and variables → Actions → Variables)
from the outputs:

| Variable | Output |
| --- | --- |
| `AWS_PLAN_ROLE_ARN` | `github_plan_role_arn` |
| `TF_STATE_BUCKET` | `state_bucket` |

They aren't secrets: the role can only be assumed by this repository's workflows.
