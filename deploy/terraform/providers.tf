provider "aws" {
  region  = var.region
  profile = var.aws_profile

  default_tags {
    tags = {
      build      = "build-04"
      project    = "cloudwatch-omni-agent-app-observability"
      managed-by = "terraform"
    }
  }
}
