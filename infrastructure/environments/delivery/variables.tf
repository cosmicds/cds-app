variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Name prefix for shared delivery resources"
  type        = string
  default     = "production"
}

variable "github_repository" {
  description = "GitHub repository in the format owner/repo"
  type        = string
  default     = "nmearl/cds-app"
}

variable "github_branch" {
  description = "GitHub branch to track for changes"
  type        = string
  default     = "main"
}

variable "approval_notification_arn" {
  description = "SNS topic ARN for approval notifications"
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
  description = "Retention in days for delivery CodeBuild CloudWatch log groups"
  type        = number
  default     = 7
}

variable "staging_portal_url" {
  description = "Staging URL shown in the approval stage"
  type        = string
}

variable "staging_cluster_name" {
  description = "Staging ECS cluster name"
  type        = string
}

variable "staging_portal_service_name" {
  description = "Staging portal ECS service name"
  type        = string
}

variable "staging_hubble_service_name" {
  description = "Staging hubble ECS service name"
  type        = string
}

variable "production_cluster_name" {
  description = "Production ECS cluster name"
  type        = string
}

variable "production_portal_service_name" {
  description = "Production portal ECS service name"
  type        = string
}

variable "production_hubble_service_name" {
  description = "Production hubble ECS service name"
  type        = string
}
