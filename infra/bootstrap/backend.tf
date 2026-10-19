# The bucket is created by this stack, so the very first apply runs on local state and
# then migrates here (see README.md).
#   terraform init -backend-config="bucket=spotify-stats-tfstate-<account id>"
terraform {
  backend "s3" {
    key          = "bootstrap/terraform.tfstate"
    region       = "eu-north-1"
    encrypt      = true
    use_lockfile = true
  }
}
