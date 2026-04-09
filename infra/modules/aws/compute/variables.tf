variable "vpc_id" {
  description = "The VPC ID"
  type        = string
}

variable "public_subnet_ids" {
  description = "Public subnet IDs for ALB"
  type        = list(string)
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for tasks"
  type        = list(string)
}

variable "backend_sg_id" {
  description = "Security group for tasks"
  type        = string
}

variable "app_role_arn" {
  description = "Execution/Task role ARN"
  type        = string
}

variable "backend_image" {
  description = "Container image for backend"
  type        = string
}

variable "db_url" {
  description = "Database connection string"
  type        = string
  sensitive   = true
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default     = {}
}
