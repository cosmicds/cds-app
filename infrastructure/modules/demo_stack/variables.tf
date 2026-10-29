variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "environment" {
  description = "Environment name used to prefix demo resources"
  type        = string
  default     = "demo"
}

variable "site_domain_name" {
  description = "Optional custom hostname for CloudFront; leave empty during the initial parallel deployment"
  type        = string
  default     = ""
}

variable "certificate_domain" {
  description = "ACM certificate domain covering site_domain_name; required when a custom hostname is set"
  type        = string
  default     = ""

  validation {
    condition     = (var.site_domain_name == "") == (var.certificate_domain == "")
    error_message = "site_domain_name and certificate_domain must either both be set or both be empty."
  }
}

variable "cds_hubble_image" {
  description = "Docker image URI for the demo Hubble service"
  type        = string
}

variable "hubble_secret_arn" {
  description = "ARN of the Secrets Manager secret containing the demo Hubble configuration"
  type        = string
}

variable "hubble_secret_names" {
  description = "Keys read from the demo Hubble Secrets Manager secret"
  type        = list(string)
  default = [
    "SOLARA_SESSION_SECRET_KEY",
    "SOLARA_OAUTH_CLIENT_ID",
    "SOLARA_OAUTH_CLIENT_SECRET",
    "SOLARA_OAUTH_API_BASE_URL",
    "SOLARA_OAUTH_SCOPE",
    "SOLARA_SESSION_HTTPS_ONLY",
    "CDS_API_KEY",
    "SOLARA_OAUTH_PRIVATE",
    "SOLARA_APP",
    "SOLARA_ROOT_PATH",
    "SOLARA_BASE_URL",
    "CDS_SHOW_TEAM_INTERFACE",
    "GOOGLE_ANALYTICS_TAG",
    "AWS_EBS_URL",
    "CDS_FORCE_DEMO",
    "CDS_DISABLE_DB",
  ]
}

variable "hubble_environment_vars" {
  description = "Plain-text environment variables for the demo Hubble task"
  type        = map(string)
  default = {
    LOG_LEVEL = "info"
    NODE_ENV  = "production"
  }
}

variable "hubble_cpu" {
  description = "CPU units for the demo Hubble Fargate task"
  type        = number
  default     = 512
}

variable "hubble_memory" {
  description = "Memory in MiB for the demo Hubble Fargate task"
  type        = number
  default     = 1024
}

variable "desired_count" {
  description = "Number of demo Hubble tasks to run when autoscaling is disabled"
  type        = number
  default     = 1
}

variable "enable_autoscaling" {
  description = "Whether to create ECS Service Auto Scaling resources"
  type        = bool
  default     = false
}

variable "min_capacity" {
  description = "Minimum task count when autoscaling is enabled"
  type        = number
  default     = 1
}

variable "max_capacity" {
  description = "Maximum task count when autoscaling is enabled"
  type        = number
  default     = 2
}

variable "autoscaling_cpu_target" {
  description = "Average CPU utilization target when autoscaling is enabled"
  type        = number
  default     = 70
}

variable "autoscaling_requests_per_target" {
  description = "ALB requests per target when autoscaling is enabled"
  type        = number
  default     = 1000
}

variable "app_log_retention_days" {
  description = "Retention period for demo application logs"
  type        = number
  default     = 3
}
