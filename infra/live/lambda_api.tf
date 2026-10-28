# The API the app talks to (stats_api.app), on a public HTTPS function URL. Requests are
# authenticated by the API itself with signed session tokens.
# Build the package first: uv run python scripts/build_lambdas.py api

data "archive_file" "api" {
  type        = "zip"
  source_dir  = "${path.module}/../../build/lambda/api"
  output_path = "${path.module}/../../build/lambda/api.zip"
}

resource "aws_iam_role" "api" {
  name               = "${var.project}-api"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

resource "aws_iam_role_policy_attachment" "api_logs" {
  role       = aws_iam_role.api.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

data "aws_iam_policy_document" "api" {
  statement {
    sid       = "ManageUsers"
    actions   = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:DeleteItem"]
    resources = [aws_dynamodb_table.users.arn]
  }

  # Recently played stores plays the poller hasn't yet, like the poller does.
  statement {
    sid     = "WritePlays"
    actions = ["s3:PutObject"]
    resources = [
      "${aws_s3_bucket.data.arn}/raw/source=api/*",
      "${aws_s3_bucket.data.arn}/listens/user=*/source=api/*",
    ]
  }

  statement {
    sid       = "ReadStats"
    actions   = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:BatchGetItem"]
    resources = [aws_dynamodb_table.stats.arn]
  }

  # DELETE /me: a user's stat documents and every file of their plays.
  statement {
    sid       = "DeleteAccountStats"
    actions   = ["dynamodb:DeleteItem", "dynamodb:BatchWriteItem"]
    resources = [aws_dynamodb_table.stats.arn]
  }

  statement {
    sid       = "ListAccountFiles"
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.data.arn]
    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values   = ["uploads/user=*", "raw/source=api/user=*", "listens/user=*"]
    }
  }

  statement {
    sid     = "DeleteAccountFiles"
    actions = ["s3:DeleteObject"]
    resources = [
      "${aws_s3_bucket.data.arn}/uploads/user=*",
      "${aws_s3_bucket.data.arn}/raw/source=api/user=*",
      "${aws_s3_bucket.data.arn}/listens/user=*",
    ]
  }

  statement {
    sid       = "ReadSettings"
    actions   = ["ssm:GetParameters", "ssm:GetParameter"]
    resources = [local.ssm_arn]
  }
}

resource "aws_iam_role_policy" "api" {
  name   = "api"
  role   = aws_iam_role.api.id
  policy = data.aws_iam_policy_document.api.json
}

resource "aws_cloudwatch_log_group" "api" {
  name              = "/aws/lambda/${var.project}-api"
  retention_in_days = 14
}

resource "aws_lambda_function" "api" {
  function_name    = "${var.project}-api"
  role             = aws_iam_role.api.arn
  runtime          = "python3.12"
  architectures    = ["arm64"]
  handler          = "stats_api.app.handler"
  filename         = data.archive_file.api.output_path
  source_code_hash = data.archive_file.api.output_base64sha256
  memory_size      = 512
  timeout          = 15

  environment {
    variables = {
      USERS_TABLE = aws_dynamodb_table.users.name
      STATS_TABLE = aws_dynamodb_table.stats.name
      DATA_BUCKET = aws_s3_bucket.data.bucket
    }
  }

  depends_on = [aws_cloudwatch_log_group.api, aws_iam_role_policy_attachment.api_logs]
}

resource "aws_lambda_function_url" "api" {
  function_name      = aws_lambda_function.api.function_name
  authorization_type = "NONE"
}

# A public function URL needs both permissions. The second only allows invocations that come
# through the URL, not direct calls from other AWS accounts.
resource "aws_lambda_permission" "api_url" {
  statement_id           = "AllowPublicFunctionUrl"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.api.function_name
  principal              = "*"
  function_url_auth_type = "NONE"
}

resource "aws_lambda_permission" "api_invoke" {
  statement_id             = "AllowPublicInvokeViaUrl"
  action                   = "lambda:InvokeFunction"
  function_name            = aws_lambda_function.api.function_name
  principal                = "*"
  invoked_via_function_url = true
}
