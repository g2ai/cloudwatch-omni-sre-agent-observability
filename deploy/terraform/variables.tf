variable "region" {
  description = "AWS Region for the workload and the Omni space."
  type        = string
  default     = "ap-south-1"
}

variable "aws_profile" {
  description = "AWS CLI profile (SSO) used by Terraform."
  type        = string
  default     = "build04"
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
