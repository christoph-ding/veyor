variable "environment" {
  type        = string
  description = "Environment name"
}

variable "account_id" {
  type        = string
  description = "AWS Account ID used for global bucket uniqueness"
}

variable "oidc_provider_arn" {
  type        = string
  description = "ARN of the EKS OIDC IAM Provider (from EKS module output)"
}

variable "oidc_provider_url" {
  type        = string
  description = "Issuer URL of the EKS OIDC Provider (from EKS module output)"
}