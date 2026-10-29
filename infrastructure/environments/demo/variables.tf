variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name used to prefix demo resources"
  type        = string
  default     = "demo"
}

variable "site_domain_name" {
  description = "Optional custom hostname for the demo CloudFront distribution"
  type        = string
  default     = ""
}

variable "certificate_domain" {
  description = "ACM certificate domain covering site_domain_name"
  type        = string
  default     = ""
}

variable "github_repository" {
  description = "GitHub repository in owner/repository format"
  type        = string
}

variable "github_branch" {
  description = "GitHub branch deployed to the demo environment"
  type        = string
  default     = "main"
}

variable "ecr_repository_name" {
  description = "Name of the dedicated demo Hubble ECR repository"
  type        = string
  default     = "cds-hubble-demo"
}

variable "enable_autoscaling" {
  description = "Whether to enable autoscaling for the demo Hubble service"
  type        = bool
  default     = false
}

variable "desired_count" {
  description = "Number of Hubble tasks when autoscaling is disabled"
  type        = number
  default     = 1
}

variable "min_capacity" {
  description = "Minimum Hubble task count when autoscaling is enabled"
  type        = number
  default     = 1
}

variable "max_capacity" {
  description = "Maximum Hubble task count when autoscaling is enabled"
  type        = number
  default     = 2
}

variable "hubble_cpu" {
  description = "CPU units for the Hubble task"
  type        = number
  default     = 512
}

variable "hubble_memory" {
  description = "Memory in MiB for the Hubble task"
  type        = number
  default     = 1024
}

variable "app_log_retention_days" {
  description = "Retention period for Hubble application logs"
  type        = number
  default     = 3
}

variable "codebuild_log_retention_days" {
  description = "Retention period for CodeBuild logs"
  type        = number
  default     = 7
}
