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

variable "budget_email" {
  description = "Email address that receives budget alerts."
  type        = string
}

variable "monthly_budget_usd" {
  description = "Monthly spend that triggers alerts. AWS Budgets bills in USD."
  type        = number
  default     = 1
}
