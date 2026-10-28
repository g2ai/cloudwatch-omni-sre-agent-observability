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
