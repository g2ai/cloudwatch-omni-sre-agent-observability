locals {
  sre_agent_name   = "sre-agent"
  sre_agent_on     = var.enable_workload ? 1 : 0
  nova_model_name  = trimprefix(var.model_id, "global.")
  nova_profile_arn = "arn:aws:bedrock:${var.region}:${data.aws_caller_identity.current.account_id}:inference-profile/${var.model_id}"
  # Built as a string, not read from the resource, so a telemetry-api update
  # does not defer this policy to apply time and show a phantom change.
  telemetry_api_arn = "arn:aws:lambda:${var.region}:${data.aws_caller_identity.current.account_id}:function:${local.telemetry_api_name}"
}

# Built by scripts/build_sre_agent.ps1. Gated so a plan without the build folder still works.
data "archive_file" "sre_agent" {
  count       = local.sre_agent_on
  type        = "zip"
  source_dir  = "${path.module}/build/sre_agent"
  output_path = "${path.module}/build/sre_agent.zip"
}

resource "aws_cloudwatch_log_group" "sre_agent" {
  count             = local.sre_agent_on
  name              = "/aws/lambda/${local.sre_agent_name}"
  retention_in_days = 3
}

resource "aws_iam_role" "sre_agent" {
  count              = local.sre_agent_on
  name               = "${local.sre_agent_name}-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

data "aws_iam_policy_document" "sre_agent" {
  count = local.sre_agent_on

  statement {
    sid       = "WriteOwnLogGroup"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.sre_agent[0].arn}:*"]
  }

  statement {
    sid       = "NovaGlobalProfileInRegion"
    actions   = ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"]
    resources = [local.nova_profile_arn]
    condition {
      test     = "StringEquals"
      variable = "aws:RequestedRegion"
      values   = [var.region]
    }
  }

  statement {
    sid       = "NovaModelInRegionViaProfile"
    actions   = ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"]
    resources = ["arn:aws:bedrock:${var.region}::foundation-model/${local.nova_model_name}"]
    condition {
      test     = "StringEquals"
      variable = "aws:RequestedRegion"
      values   = [var.region]
    }
    condition {
      test     = "StringEquals"
      variable = "bedrock:InferenceProfileArn"
      values   = [local.nova_profile_arn]
    }
  }

  statement {
    sid       = "NovaViaGlobalProfileAnyRegion"
    actions   = ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"]
    resources = ["arn:aws:bedrock:::foundation-model/${local.nova_model_name}"]
    condition {
      test     = "StringEquals"
      variable = "aws:RequestedRegion"
      values   = ["unspecified"]
    }
    condition {
      test     = "StringEquals"
      variable = "bedrock:InferenceProfileArn"
      values   = [local.nova_profile_arn]
    }
  }

  statement {
    sid       = "TelemetryApiUrlOnly"
    actions   = ["lambda:InvokeFunctionUrl"]
    resources = [local.telemetry_api_arn]
    condition {
      test     = "StringEquals"
      variable = "lambda:FunctionUrlAuthType"
      values   = ["AWS_IAM"]
    }
  }

  statement {
    sid       = "TelemetryApiInvokeViaUrl"
    actions   = ["lambda:InvokeFunction"]
    resources = [local.telemetry_api_arn]
    condition {
      test     = "Bool"
      variable = "lambda:InvokedViaFunctionUrl"
      values   = ["true"]
    }
  }
}

resource "aws_iam_role_policy" "sre_agent" {
  count  = local.sre_agent_on
  name   = "sre-agent-least-privilege"
  role   = aws_iam_role.sre_agent[0].id
  policy = data.aws_iam_policy_document.sre_agent[0].json
}

resource "aws_iam_role_policy_attachment" "sre_agent_xray" {
  count      = local.sre_agent_on
  role       = aws_iam_role.sre_agent[0].name
  policy_arn = "arn:aws:iam::aws:policy/AWSXrayWriteOnlyAccess"
}

resource "aws_lambda_function" "sre_agent" {
  count            = local.sre_agent_on
  function_name    = local.sre_agent_name
  role             = aws_iam_role.sre_agent[0].arn
  runtime          = "python3.13"
  architectures    = ["x86_64"]
  handler          = "agent.handler"
  filename         = data.archive_file.sre_agent[0].output_path
  source_code_hash = data.archive_file.sre_agent[0].output_base64sha256
  memory_size      = 1024
  timeout          = 60
  layers           = [var.adot_python_layer_arn]

  tracing_config {
    mode = "Active"
  }

  environment {
    variables = {
      AWS_LAMBDA_EXEC_WRAPPER               = "/opt/otel-instrument"
      OTEL_SERVICE_NAME                     = local.sre_agent_name
      AGENT_OBSERVABILITY_ENABLED           = "true"
      AWS_GENAI_CONTENT_EXTRACTION_OPT_OUT  = "true"
      OTEL_PYTHON_DISTRO                    = "aws_distro"
      OTEL_PYTHON_CONFIGURATOR              = "aws_configurator"
      OTEL_PYTHON_DISABLED_INSTRUMENTATIONS = "none"
      OTEL_AWS_APPLICATION_SIGNALS_ENABLED  = "false"
      OTEL_EXPORTER_OTLP_PROTOCOL           = "http/protobuf"
      OTEL_TRACES_EXPORTER                  = "otlp"
      OTEL_LOGS_EXPORTER                    = "none"
      OTEL_METRICS_EXPORTER                 = "none"
      TELEMETRY_API_URL                     = aws_lambda_function_url.telemetry_api[0].function_url
      MODEL_ID                              = var.model_id
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.sre_agent,
    aws_iam_role_policy.sre_agent,
  ]
}

resource "aws_lambda_function_url" "sre_agent" {
  count              = local.sre_agent_on
  function_name      = aws_lambda_function.sre_agent[0].function_name
  authorization_type = "AWS_IAM"
}
