# Settings and secrets the Lambdas read at start-up. Terraform creates each parameter with a
# placeholder and then leaves its value alone: real secrets are written by
# scripts/put_secrets.py from your .env, so they never pass through Terraform state.

locals {
  ssm_prefix = "/${var.project}"
  ssm_arn    = "arn:aws:ssm:${var.region}:${data.aws_caller_identity.current.account_id}:parameter${local.ssm_prefix}/*"
}

resource "aws_ssm_parameter" "secret" {
  for_each = toset(["spotify_client_id", "spotify_client_secret", "session_secret"])

  name  = "${local.ssm_prefix}/${each.key}"
  type  = "SecureString"
  value = "set-by-scripts/put_secrets.py"

  lifecycle {
    ignore_changes = [value]
  }
}

# Where Spotify sends users back after they log in: the API's callback. It must also be listed
# under Redirect URIs in the Spotify developer dashboard.
resource "aws_ssm_parameter" "spotify_redirect_uri" {
  name  = "${local.ssm_prefix}/spotify_redirect_uri"
  type  = "String"
  value = "${aws_lambda_function_url.api.function_url}auth/callback"
}
