provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project   = var.project
      ManagedBy = "terraform"
      Stack     = "live"
    }
  }
}

data "aws_caller_identity" "current" {}
