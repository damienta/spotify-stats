#!/usr/bin/env bash
# Applies infra/bootstrap from AWS CloudShell, which runs as your console identity.
# Usage (in CloudShell):
#   curl -fsSL https://raw.githubusercontent.com/damienta/spotify-stats/main/scripts/cloudshell-bootstrap.sh | BUDGET_EMAIL=you@example.com bash
set -euo pipefail

: "${BUDGET_EMAIL:?Set BUDGET_EMAIL}"
BRANCH="${BRANCH:-main}"
TF_VERSION="1.16.5"
REGION="eu-west-2"

echo "==> Checking this identity can use AWS services"
aws sts get-caller-identity --query Arn --output text
aws dynamodb list-tables --region "$REGION" --output text >/dev/null
ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
BUCKET="spotify-stats-tfstate-${ACCOUNT_ID}"

echo "==> Installing Terraform ${TF_VERSION}"
mkdir -p "$HOME/bin"
if ! "$HOME/bin/terraform" version 2>/dev/null | grep -q "v${TF_VERSION}"; then
  curl -fsSLo /tmp/tf.zip "https://releases.hashicorp.com/terraform/${TF_VERSION}/terraform_${TF_VERSION}_linux_amd64.zip"
  unzip -o -q /tmp/tf.zip terraform -d "$HOME/bin" && rm /tmp/tf.zip
fi
export PATH="$HOME/bin:$PATH"

echo "==> Getting the repo (${BRANCH})"
if [ -d "$HOME/spotify-stats/.git" ]; then
  git -C "$HOME/spotify-stats" fetch -q origin "$BRANCH"
  git -C "$HOME/spotify-stats" checkout -q -B "$BRANCH" "origin/$BRANCH"
else
  git clone -q -b "$BRANCH" https://github.com/damienta/spotify-stats.git "$HOME/spotify-stats"
fi
cd "$HOME/spotify-stats/infra/bootstrap"

export TF_VAR_budget_email="$BUDGET_EMAIL"
export TF_IN_AUTOMATION=1

if aws s3api head-bucket --bucket "$BUCKET" 2>/dev/null; then
  echo "==> State bucket exists: using remote state"
  terraform init -input=false -backend-config="bucket=${BUCKET}"
else
  echo "==> First run: local state until the bucket exists"
  mv backend.tf /tmp/backend.tf.bak
  trap 'mv -f /tmp/backend.tf.bak backend.tf 2>/dev/null || true' EXIT
  terraform init -input=false
  # The budget may already exist from an earlier partial apply.
  if aws budgets describe-budget --account-id "$ACCOUNT_ID" --budget-name spotify-stats-monthly >/dev/null 2>&1 \
     && ! terraform state show aws_budgets_budget.monthly >/dev/null 2>&1; then
    terraform import -input=false aws_budgets_budget.monthly "${ACCOUNT_ID}:spotify-stats-monthly"
  fi
fi

terraform apply -input=false -auto-approve

if [ -f /tmp/backend.tf.bak ]; then
  echo "==> Moving state into ${BUCKET}"
  mv -f /tmp/backend.tf.bak backend.tf
  trap - EXIT
  terraform init -input=false -migrate-state -force-copy -backend-config="bucket=${BUCKET}"
  rm -f terraform.tfstate terraform.tfstate.backup
fi

echo
echo "==> Done. Outputs:"
terraform output
