locals {
  freshness_evaluator_name = "freshness-evaluator"
  freshness_evaluator_on   = var.enable_workload ? 1 : 0
}

data "archive_file" "freshness_evaluator" {
  type        = "zip"
  source_file = "${path.module}/../../src/freshness_evaluator/evaluator.py"
  output_path = "${path.module}/build/freshness_evaluator.zip"
}

resource "aws_cloudwatch_log_group" "freshness_evaluator" {
  count             = local.freshness_evaluator_on
  name              = "/aws/lambda/${local.freshness_evaluator_name}"
  retention_in_days = 3
}

resource "aws_iam_role" "freshness_evaluator" {
  count              = local.freshness_evaluator_on
  name               = "${local.freshness_evaluator_name}-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

data "aws_iam_policy_document" "freshness_evaluator_logs" {
  count = local.freshness_evaluator_on
  statement {
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.freshness_evaluator[0].arn}:*"]
  }
}

resource "aws_iam_role_policy" "freshness_evaluator_logs" {
  count  = local.freshness_evaluator_on
  name   = "write-own-log-group"
  role   = aws_iam_role.freshness_evaluator[0].id
  policy = data.aws_iam_policy_document.freshness_evaluator_logs[0].json
}

# Code-based evaluator for AgentCore Evaluations. No ADOT layer, no tracing:
# its own spans must not mix into the agent traces it scores.
resource "aws_lambda_function" "freshness_evaluator" {
  count            = local.freshness_evaluator_on
  function_name    = local.freshness_evaluator_name
  role             = aws_iam_role.freshness_evaluator[0].arn
  runtime          = "python3.13"
  architectures    = ["x86_64"]
  handler          = "evaluator.handler"
  filename         = data.archive_file.freshness_evaluator.output_path
  source_code_hash = data.archive_file.freshness_evaluator.output_base64sha256
  memory_size      = 256
  timeout          = 30

  environment {
    variables = {
      FRESHNESS_MAX_AGE_MINUTES = "15"
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.freshness_evaluator,
    aws_iam_role_policy.freshness_evaluator_logs,
  ]
}
