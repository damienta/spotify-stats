variable "region" {
  description = "AWS region for everything in this project."
  type        = string
  default     = "eu-north-1"
}

variable "project" {
  description = "Name used as a prefix and tag on every resource."
  type        = string
  default     = "spotify-stats"
}

variable "app_hosts" {
  description = "Hosted web app addresses login may send people back to (e.g. [\"stats-abc.pages.dev\"]). Preview deployments (<id>.<host>) are allowed too. Set in terraform.tfvars."
  type        = list(string)
  default     = []
}
