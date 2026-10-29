terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

module "app_stack" {
  source = "../../modules/app_stack"

  aws_region                        = var.aws_region
  environment                       = var.environment
  site_domain_name                  = var.site_domain_name
  certificate_domain                = var.certificate_domain
  cds_portal_image                  = var.cds_portal_image
  cds_hubble_image                  = var.cds_hubble_image
  cds_portal_min_capacity           = var.cds_portal_min_capacity
  cds_portal_max_capacity           = var.cds_portal_max_capacity
  cds_hubble_min_capacity           = var.cds_hubble_min_capacity
  cds_hubble_max_capacity           = var.cds_hubble_max_capacity
  enable_autoscaling                = var.enable_autoscaling
  enable_cluster_capacity_providers = var.enable_cluster_capacity_providers
  enable_container_insights         = var.enable_container_insights
  use_capacity_provider_strategy    = var.use_capacity_provider_strategy
  use_private_service_subnets       = var.use_private_service_subnets
  create_private_nat_gateways       = var.create_private_nat_gateways
  log_group_class                   = var.log_group_class
  app_log_retention_days            = var.app_log_retention_days
  cds_portal_cpu                    = var.cds_portal_cpu
  cds_portal_memory                 = var.cds_portal_memory
  cds_hubble_cpu                    = var.cds_hubble_cpu
  cds_hubble_memory                 = var.cds_hubble_memory
  portal_environment_vars           = var.portal_environment_vars
  hubble_environment_vars           = var.hubble_environment_vars
  portal_secret_names               = var.portal_secret_names
  hubble_secret_names               = var.hubble_secret_names
}
