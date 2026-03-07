variable "function_name" {
  description = "Name of the lambda function"
  type        = string
}

variable "handler" {
  description = "The function entrypoint"
  type        = string
  default     = "main.handler"
}

variable "runtime" {
  description = "The runtime environment"
  type        = string
  default     = "python3.12"
}

variable "filename" {
  description = "Path to the function's deployment package"
  type        = string
}

variable "app_role_arn" {
  description = "IAM role for the lambda"
  type        = string
}

variable "subnet_ids" {
  description = "Subnets for VPC execution"
  type        = list(string)
  default     = []
}

variable "security_group_ids" {
  description = "Security groups for VPC execution"
  type        = list(string)
  default     = []
}

variable "environment_variables" {
  description = "A map of environment variables"
  type        = map(string)
  default     = {}
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
