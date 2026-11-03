variable "region" {
  description = "AWS Region for the workload and the Omni space."
  type        = string
  default     = "ap-south-1"
}

variable "aws_profile" {
  description = "AWS CLI profile (SSO) used by Terraform. Null uses AWS_PROFILE or the default credential chain."
  type        = string
  default     = null
}

variable "enable_workload" {
  description = "Create the paid workload (Lambdas, SNS, evaluator). Off by default."
  type        = bool
  default     = false
}

variable "cache_mode" {
  description = "telemetry-api data mode. fresh = healthy service, stale = the bad deploy (old cached data, HTTP 200)."
  type        = string
  default     = "fresh"

  validation {
    condition     = contains(["fresh", "stale"], var.cache_mode)
    error_message = "cache_mode must be fresh or stale."
  }
}

variable "adot_python_layer_arn" {
  description = "AWS Lambda Layer for OpenTelemetry (Python), pinned per Region."
  type        = string
  default     = "arn:aws:lambda:ap-south-1:615299751070:layer:AWSOpenTelemetryDistroPython:29"
}

variable "model_id" {
  description = "Bedrock global inference profile ID for the agent."
  type        = string
  default     = "global.amazon.nova-2-lite-v1:0"

  validation {
    condition     = startswith(var.model_id, "global.")
    error_message = "model_id must be a global inference profile (global.*); the IAM policy assumes it."
  }
}

# Account-specific values live in terraform.tfvars (gitignored).
# See terraform.tfvars.example.
variable "omni_space_role_name" {
  description = "IAM role created by your CloudWatch Omni space setup (CloudWatchOmniSpaceAccessRole-...). Runs on-demand evaluations."
  type        = string
  default     = ""

  validation {
    condition     = !var.enable_workload || var.omni_space_role_name != ""
    error_message = "Set omni_space_role_name in terraform.tfvars (see terraform.tfvars.example)."
  }
}

variable "evaluation_role_name" {
  description = "IAM role created by your CloudWatch Omni space setup for online evaluations (AgentCoreEvaluationRole-...)."
  type        = string
  default     = ""

  validation {
    condition     = !var.enable_workload || var.evaluation_role_name != ""
    error_message = "Set evaluation_role_name in terraform.tfvars (see terraform.tfvars.example)."
  }
}
