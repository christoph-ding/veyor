variable "environment" {
  type        = string
  description = "Environment name"
}

variable "vpc_id" {
  type        = string
  description = "VPC ID where EKS nodes will run"
}

variable "private_subnet_ids" {
  type        = list(string)
  description = "Subnet IDs for EKS worker nodes"
}

variable "instance_types" {
  type        = list(string)
  description = "EC2 Instance types for worker nodes"
  default     = ["t3.medium"]
}

variable "desired_size" {
  type        = number
  description = "Initial desired worker node count"
  default     = 2
}