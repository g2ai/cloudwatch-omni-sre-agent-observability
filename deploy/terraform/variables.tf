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
