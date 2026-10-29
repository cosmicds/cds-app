variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "environment" {
  description = "Environment name used to prefix demo delivery resources"
  type        = string
  default     = "demo"
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
}

variable "ecr_repository_arn" {
  description = "ARN of the dedicated demo Hubble ECR repository"
  type        = string
}

variable "ecs_cluster_name" {
  description = "Name of the demo ECS cluster"
  type        = string
}

variable "ecs_service_name" {
  description = "Name of the demo Hubble ECS service"
  type        = string
}

variable "codebuild_log_retention_days" {
  description = "Retention period for demo build and deploy logs"
  type        = number
  default     = 7
}
