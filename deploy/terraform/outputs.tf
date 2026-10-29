output "account_id" {
  description = "Account Terraform is running against."
  value       = data.aws_caller_identity.current.account_id
}

output "region" {
  description = "Region in use."
  value       = var.region
}

output "workload_enabled" {
  description = "Whether paid resources are switched on."
  value       = var.enable_workload
}

output "telemetry_api_url" {
  description = "Function URL (IAM auth, SigV4)."
  value       = one(aws_lambda_function_url.telemetry_api[*].function_url)
}

output "telemetry_api_arn" {
  description = "telemetry-api function ARN, for the agent IAM policy."
  value       = one(aws_lambda_function.telemetry_api[*].arn)
}

output "sre_agent_url" {
  description = "sre-agent function URL (IAM auth, SigV4 POST)."
  value       = one(aws_lambda_function_url.sre_agent[*].function_url)
}

output "freshness_evaluator_arn" {
  description = "Lambda ARN for the AgentCore code-based evaluator."
  value       = one(aws_lambda_function.freshness_evaluator[*].arn)
}
