terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }

    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

module "release_pipeline" {
  source = "../../modules/release_pipeline"

  aws_region                     = var.aws_region
  environment                    = var.environment
  github_repository              = var.github_repository
  github_branch                  = var.github_branch
  approval_notification_arn      = var.approval_notification_arn
  portal_repository_name         = var.portal_repository_name
  hubble_repository_name         = var.hubble_repository_name
  codebuild_log_retention_days   = var.codebuild_log_retention_days
  staging_portal_url             = var.staging_portal_url
  staging_cluster_name           = var.staging_cluster_name
  staging_portal_service_name    = var.staging_portal_service_name
  staging_hubble_service_name    = var.staging_hubble_service_name
  production_cluster_name        = var.production_cluster_name
  production_portal_service_name = var.production_portal_service_name
  production_hubble_service_name = var.production_hubble_service_name
}
