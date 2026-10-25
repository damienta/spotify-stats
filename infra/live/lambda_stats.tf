# The stats job: every hour, rebuilds each user's stat documents (stats_jobs.job).
# Build the package first: uv run python scripts/build_lambdas.py stats

data "archive_file" "stats" {
  type        = "zip"
  source_dir  = "${path.module}/../../build/lambda/stats"
  output_path = "${path.module}/../../build/lambda/stats.zip"
}

resource "aws_iam_role" "stats" {
  name               = "${var.project}-stats"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

resource "aws_iam_role_policy_attachment" "stats_logs" {
  role       = aws_iam_role.stats.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

data "aws_iam_policy_document" "stats" {
  statement {
    sid       = "ListUsers"
    actions   = ["dynamodb:Scan"]
    resources = [aws_dynamodb_table.users.arn]
  }

  statement {
    sid       = "WriteStats"
    actions   = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:BatchWriteItem"]
    resources = [aws_dynamodb_table.stats.arn]
  }

  statement {
    sid       = "ListListens"
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.data.arn]

    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values   = ["listens/*"]
    }
  }

  statement {
    sid       = "ReadAndCompactListens"
    actions   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
    resources = ["${aws_s3_bucket.data.arn}/listens/*"]
  }
}

resource "aws_iam_role_policy" "stats" {
  name   = "stats"
  role   = aws_iam_role.stats.id
  policy = data.aws_iam_policy_document.stats.json
}

resource "aws_cloudwatch_log_group" "stats" {
  name              = "/aws/lambda/${var.project}-stats"
  retention_in_days = 14
}

resource "aws_lambda_function" "stats" {
  function_name    = "${var.project}-stats"
  role             = aws_iam_role.stats.arn
  runtime          = "python3.12"
  architectures    = ["arm64"]
  handler          = "stats_jobs.job.handler"
  filename         = data.archive_file.stats.output_path
  source_code_hash = data.archive_file.stats.output_base64sha256
  memory_size      = 1536
  timeout          = 300

  environment {
    variables = {
      USERS_TABLE = aws_dynamodb_table.users.name
      STATS_TABLE = aws_dynamodb_table.stats.name
      DATA_BUCKET = aws_s3_bucket.data.bucket
      # DuckDB keeps its extension cache under HOME; /tmp is the only writable path in Lambda.
      HOME = "/tmp"
    }
  }

  depends_on = [aws_cloudwatch_log_group.stats, aws_iam_role_policy_attachment.stats_logs]
}

resource "aws_cloudwatch_event_rule" "stats" {
  name                = "${var.project}-stats"
  description         = "Rebuild stat documents from new listens."
  schedule_expression = "rate(1 hour)"
}

resource "aws_cloudwatch_event_target" "stats" {
  rule = aws_cloudwatch_event_rule.stats.name
  arn  = aws_lambda_function.stats.arn
}

resource "aws_lambda_permission" "stats_schedule" {
  statement_id  = "AllowSchedule"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.stats.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.stats.arn
}
