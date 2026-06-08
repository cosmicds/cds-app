variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "environment" {
  description = "Name prefix for shared delivery resources"
  type        = string
}

variable "github_repository" {
  description = "GitHub repository in the format owner/repo"
  type        = string
}

variable "github_branch" {
  description = "GitHub branch to track for changes"
  type        = string
  default     = "main"
}

variable "approval_notification_arn" {
  description = "SNS topic ARN for manual approval notifications"
  type        = string
  default     = ""
}

variable "portal_repository_name" {
  description = "ECR repository name for cds-portal"
  type        = string
  default     = "cds-portal"
}

variable "hubble_repository_name" {
  description = "ECR repository name for cds-hubble"
  type        = string
  default     = "cds-hubble"
}

variable "codebuild_log_retention_days" {
  description = "Retention in days for CodeBuild CloudWatch log groups"
  type        = number
  default     = 14
}

variable "staging_portal_url" {
  description = "Staging URL shown in the manual approval step"
  type        = string
}

variable "staging_cluster_name" {
  description = "ECS cluster name for staging"
  type        = string
}

variable "staging_portal_service_name" {
  description = "CDS Portal ECS service name in staging"
  type        = string
}

variable "staging_hubble_service_name" {
  description = "CDS Hubble ECS service name in staging"
  type        = string
}

variable "production_cluster_name" {
  description = "ECS cluster name for production"
  type        = string
}

variable "production_portal_service_name" {
  description = "CDS Portal ECS service name in production"
  type        = string
}

variable "production_hubble_service_name" {
  description = "CDS Hubble ECS service name in production"
  type        = string
}
