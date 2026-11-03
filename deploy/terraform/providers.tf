provider "aws" {
  region  = var.region
  profile = var.aws_profile

  default_tags {
    tags = {
      build      = "build-04"
      project    = "cloudwatch-omni-sre-agent-observability"
      managed-by = "terraform"
    }
  }
}
