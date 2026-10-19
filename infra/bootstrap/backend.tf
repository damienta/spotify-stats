# The bucket is created by this stack, so the very first apply runs on local state and
# then migrates here (scripts/cloudshell-bootstrap.sh does both).
#   terraform init -backend-config="bucket=spotify-stats-tfstate-<account id>"
terraform {
  backend "s3" {
    key          = "bootstrap/terraform.tfstate"
    region       = "eu-west-2"
    encrypt      = true
    use_lockfile = true
  }
}
