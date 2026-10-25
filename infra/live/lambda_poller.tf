# The poller: every 20 minutes, stores each user's new plays in S3 (stats_ingest.poller).
# Build the package first: uv run python scripts/build_lambdas.py poller

data "archive_file" "poller" {
  type        = "zip"
  source_dir  = "${path.module}/../../build/lambda/poller"
  output_path = "${path.module}/../../build/lambda/poller.zip"
}

data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "poller" {
  name               = "${var.project}-poller"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

resource "aws_iam_role_policy_attachment" "poller_logs" {
  role       = aws_iam_role.poller.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

data "aws_iam_policy_document" "poller" {
  statement {
    sid       = "ReadAndUpdateUsers"
    actions   = ["dynamodb:Scan", "dynamodb:GetItem", "dynamodb:UpdateItem"]
    resources = [aws_dynamodb_table.users.arn]
  }

  statement {
    sid     = "WritePlays"
    actions = ["s3:PutObject"]
    resources = [
      "${aws_s3_bucket.data.arn}/raw/source=api/*",
      "${aws_s3_bucket.data.arn}/listens/*",
    ]
  }

  statement {
    sid       = "ReadSettings"
    actions   = ["ssm:GetParameters", "ssm:GetParameter"]
    resources = [local.ssm_arn]
  }
}

resource "aws_iam_role_policy" "poller" {
  name   = "poller"
  role   = aws_iam_role.poller.id
  policy = data.aws_iam_policy_document.poller.json
}

resource "aws_cloudwatch_log_group" "poller" {
  name              = "/aws/lambda/${var.project}-poller"
  retention_in_days = 14
}

resource "aws_lambda_function" "poller" {
  function_name    = "${var.project}-poller"
  role             = aws_iam_role.poller.arn
  runtime          = "python3.12"
  architectures    = ["arm64"]
  handler          = "stats_ingest.poller.handler"
  filename         = data.archive_file.poller.output_path
  source_code_hash = data.archive_file.poller.output_base64sha256
  memory_size      = 256
  timeout          = 120

  environment {
    variables = {
      USERS_TABLE = aws_dynamodb_table.users.name
      DATA_BUCKET = aws_s3_bucket.data.bucket
    }
  }

  depends_on = [aws_cloudwatch_log_group.poller, aws_iam_role_policy_attachment.poller_logs]
}

resource "aws_cloudwatch_event_rule" "poller" {
  name                = "${var.project}-poller"
  description         = "Poll Spotify before anyone's last-50 history rolls over."
  schedule_expression = "rate(20 minutes)"
}

resource "aws_cloudwatch_event_target" "poller" {
  rule = aws_cloudwatch_event_rule.poller.name
  arn  = aws_lambda_function.poller.arn
}

resource "aws_lambda_permission" "poller_schedule" {
  statement_id  = "AllowSchedule"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.poller.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.poller.arn
}
