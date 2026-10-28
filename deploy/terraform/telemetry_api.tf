locals {
  telemetry_api_name = "telemetry-api"
  telemetry_api_on   = var.enable_workload ? 1 : 0
}

data "archive_file" "telemetry_api" {
  type        = "zip"
  source_dir  = "${path.module}/../../src/telemetry_api"
  output_path = "${path.module}/build/telemetry_api.zip"
  excludes    = ["__pycache__", "test_handler.py"]
}

resource "aws_cloudwatch_log_group" "telemetry_api" {
  count             = local.telemetry_api_on
  name              = "/aws/lambda/${local.telemetry_api_name}"
  retention_in_days = 3
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

resource "aws_iam_role" "telemetry_api" {
  count              = local.telemetry_api_on
  name               = "${local.telemetry_api_name}-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

data "aws_iam_policy_document" "telemetry_api_logs" {
  count = local.telemetry_api_on
  statement {
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.telemetry_api[0].arn}:*"]
  }
}

resource "aws_iam_role_policy" "telemetry_api_logs" {
  count  = local.telemetry_api_on
  name   = "write-own-log-group"
  role   = aws_iam_role.telemetry_api[0].id
  policy = data.aws_iam_policy_document.telemetry_api_logs[0].json
}

resource "aws_iam_role_policy_attachment" "telemetry_api_appsignals" {
  count      = local.telemetry_api_on
  role       = aws_iam_role.telemetry_api[0].name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchLambdaApplicationSignalsExecutionRolePolicy"
}

resource "aws_iam_role_policy_attachment" "telemetry_api_xray" {
  count      = local.telemetry_api_on
  role       = aws_iam_role.telemetry_api[0].name
  policy_arn = "arn:aws:iam::aws:policy/AWSXrayWriteOnlyAccess"
}

resource "aws_lambda_function" "telemetry_api" {
  count            = local.telemetry_api_on
  function_name    = local.telemetry_api_name
  role             = aws_iam_role.telemetry_api[0].arn
  runtime          = "python3.13"
  architectures    = ["x86_64"]
  handler          = "handler.handler"
  filename         = data.archive_file.telemetry_api.output_path
  source_code_hash = data.archive_file.telemetry_api.output_base64sha256
  memory_size      = 256
  timeout          = 10
  layers           = [var.adot_python_layer_arn]

  tracing_config {
    mode = "Active"
  }

  environment {
    variables = {
      AWS_LAMBDA_EXEC_WRAPPER = "/opt/otel-instrument"
      OTEL_SERVICE_NAME       = local.telemetry_api_name
      CACHE_MODE              = var.cache_mode
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.telemetry_api,
    aws_iam_role_policy.telemetry_api_logs,
  ]
}

resource "aws_lambda_function_url" "telemetry_api" {
  count              = local.telemetry_api_on
  function_name      = aws_lambda_function.telemetry_api[0].function_name
  authorization_type = "AWS_IAM"
}
