terraform {
  required_version = ">= 1.10"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }

  # The bucket comes from the bootstrap stack and is passed at init time:
  #   terraform init -backend-config="bucket=<state_bucket output>"
  backend "s3" {
    key          = "live/terraform.tfstate"
    region       = "eu-west-2"
    encrypt      = true
    use_lockfile = true
  }
}
