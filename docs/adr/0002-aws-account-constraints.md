# 2. Working within the AWS account's managed restrictions

Date: 2026-10-19
Status: Accepted

## Context

The AWS account was created through AWS's newer project-based sign-up. It sits in an
AWS-managed organization whose service control policies we can't change:

- Only **eu-north-1** is allowed. Requests to other regions are denied, even for
  administrators. Global services (IAM, Budgets) still work.
- **Creating IAM OIDC identity providers is denied**, so GitHub Actions can't get
  short-lived AWS credentials through OIDC.
- `aws login` doesn't support this account's sign-in. Workstation access uses an IAM user
  whose credentials stay in `~/.aws/credentials`.

## Decision

- Every stack uses eu-north-1.
- CI checks formatting and validates every stack without touching AWS. `terraform plan` and
  `apply` run from a workstation. No AWS keys are stored in GitHub.
- The bootstrap stack creates only the state bucket and the budget alarm.

## Consequences

- Pull requests don't get a plan preview from CI. Plans are run locally before merging.
- If the account later allows OIDC providers or more regions, the GitHub OIDC plan role can be
  added back to the bootstrap stack and the plan job restored in `.github/workflows/terraform.yml`.
