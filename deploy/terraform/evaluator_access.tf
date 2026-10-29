# The Omni space roles were created by the console. Terraform only adds a scoped
# inline policy to each, so `terraform destroy` removes exactly what we added.
data "aws_iam_role" "omni_space" {
  count = local.freshness_evaluator_on
  name  = var.omni_space_role_name
}

data "aws_iam_role" "evaluation" {
  count = local.freshness_evaluator_on
  name  = var.evaluation_role_name
}

data "aws_iam_policy_document" "invoke_freshness_evaluator" {
  count = local.freshness_evaluator_on
  statement {
    sid       = "InvokeFreshnessEvaluator"
    actions   = ["lambda:InvokeFunction", "lambda:GetFunction"]
    resources = [aws_lambda_function.freshness_evaluator[0].arn]
  }
}

resource "aws_iam_role_policy" "omni_space_invoke_evaluator" {
  count  = local.freshness_evaluator_on
  name   = "invoke-freshness-evaluator"
  role   = data.aws_iam_role.omni_space[0].name
  policy = data.aws_iam_policy_document.invoke_freshness_evaluator[0].json
}

resource "aws_iam_role_policy" "evaluation_invoke_evaluator" {
  count  = local.freshness_evaluator_on
  name   = "invoke-freshness-evaluator"
  role   = data.aws_iam_role.evaluation[0].name
  policy = data.aws_iam_policy_document.invoke_freshness_evaluator[0].json
}
