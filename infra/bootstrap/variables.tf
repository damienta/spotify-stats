variable "region" {
  description = "AWS region for everything in this project."
  type        = string
  default     = "eu-west-2"
}

variable "project" {
  description = "Name used as a prefix and tag on every resource."
  type        = string
  default     = "spotify-stats"
}
