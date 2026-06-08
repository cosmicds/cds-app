variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "site_domain_name" {
  description = "Primary DNS name for this environment"
  type        = string
}

variable "certificate_domain" {
  description = "Domain name used to look up the ACM certificate for ALB and CloudFront"
  type        = string
}

variable "cds_portal_image" {
  description = "Docker image URI for cds-portal"
  type        = string
}

variable "cds_hubble_image" {
  description = "Docker image URI for cds-hubble"
  type        = string
}

variable "cds_portal_min_capacity" {
  description = "Minimum number of tasks for cds-portal"
  type        = number
  default     = 1
}

variable "cds_portal_max_capacity" {
  description = "Maximum number of tasks for cds-portal"
  type        = number
  default     = 10
}

variable "cds_hubble_min_capacity" {
  description = "Minimum number of tasks for cds-hubble"
  type        = number
  default     = 1
}

variable "cds_hubble_max_capacity" {
  description = "Maximum number of tasks for cds-hubble"
  type        = number
  default     = 10
}

variable "enable_autoscaling" {
  description = "Whether to create ECS Service Auto Scaling resources"
  type        = bool
  default     = true
}

variable "enable_cluster_capacity_providers" {
  description = "Whether to manage ECS cluster capacity providers"
  type        = bool
  default     = false
}

variable "enable_container_insights" {
  description = "Whether to enable ECS Container Insights for the cluster"
  type        = bool
  default     = false
}

variable "use_capacity_provider_strategy" {
  description = "Whether ECS services should use capacity provider strategy instead of launch_type"
  type        = bool
  default     = false
}

variable "use_private_service_subnets" {
  description = "Whether ECS services should run in private subnets"
  type        = bool
  default     = true
}

variable "create_private_nat_gateways" {
  description = "Whether to create NAT gateways and private route tables for private subnets"
  type        = bool
  default     = true
}

variable "log_group_class" {
  description = "CloudWatch log group class to use for application logs"
  type        = string
  default     = "STANDARD"
}

variable "app_log_retention_days" {
  description = "Retention in days for application CloudWatch log groups"
  type        = number
  default     = 7
}

variable "cloudfront_origin_protocol_policy" {
  description = "Protocol policy CloudFront uses when connecting to the ALB origin"
  type        = string
  default     = "https-only"
}

variable "cds_portal_cpu" {
  description = "CPU units for the cds-portal task definition"
  type        = number
  default     = 256
}

variable "cds_portal_memory" {
  description = "Memory in MiB for the cds-portal task definition"
  type        = number
  default     = 512
}

variable "cds_hubble_cpu" {
  description = "CPU units for the cds-hubble task definition"
  type        = number
  default     = 1024
}

variable "cds_hubble_memory" {
  description = "Memory in MiB for the cds-hubble task definition"
  type        = number
  default     = 2048
}

variable "portal_environment_vars" {
  description = "Plain-text environment variables for cds-portal"
  type        = map(string)
  default = {
    LOG_LEVEL = "info"
    NODE_ENV  = "production"
  }
}

variable "hubble_environment_vars" {
  description = "Plain-text environment variables for cds-hubble"
  type        = map(string)
  default = {
    LOG_LEVEL = "info"
    NODE_ENV  = "production"
  }
}

variable "portal_secret_names" {
  description = "Secret keys expected in the CDS Portal secret"
  type        = list(string)
  default = [
    "SOLARA_SESSION_SECRET_KEY",
    "SOLARA_OAUTH_CLIENT_ID",
    "SOLARA_OAUTH_CLIENT_SECRET",
    "SOLARA_OAUTH_API_BASE_URL",
    "SOLARA_OAUTH_SCOPE",
    "SOLARA_SESSION_HTTPS_ONLY",
    "CDS_API_KEY",
    "SOLARA_APP",
    "SOLARA_BASE_URL",
    "AWS_EBS_URL",
    "EMAIL_PASSWORD",
    "EMAIL_SERVICE",
    "EMAIL_USERNAME",
  ]
}

variable "portal_secret_source_arn" {
  description = "Optional source Secrets Manager ARN used to seed the CDS Portal secret value"
  type        = string
  default     = null
}

variable "hubble_secret_names" {
  description = "Secret keys expected in the CDS Hubble secret"
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
  ]
}

variable "hubble_secret_source_arn" {
  description = "Optional source Secrets Manager ARN used to seed the CDS Hubble secret value"
  type        = string
  default     = null
}
