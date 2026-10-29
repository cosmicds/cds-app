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

resource "aws_ecr_repository" "hubble" {
  name                 = var.ecr_repository_name
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name        = "${var.environment}-cds-hubble-ecr"
    Environment = var.environment
  }
}

resource "aws_ecr_lifecycle_policy" "hubble" {
  repository = aws_ecr_repository.hubble.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Remove untagged demo images after seven days"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 7
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 2
        description  = "Retain only the ten newest demo images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 10
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

resource "aws_secretsmanager_secret" "hubble" {
  name                    = "${var.environment}/cds-hubble/secrets"
  description             = "Manually managed configuration for the Hubble demo"
  recovery_window_in_days = 7

  tags = {
    Name        = "${var.environment}-cds-hubble-secrets"
    Environment = var.environment
  }
}

module "demo_stack" {
  source = "../../modules/demo_stack"

  aws_region             = var.aws_region
  environment            = var.environment
  site_domain_name       = var.site_domain_name
  certificate_domain     = var.certificate_domain
  cds_hubble_image       = "${aws_ecr_repository.hubble.repository_url}:latest"
  hubble_secret_arn      = aws_secretsmanager_secret.hubble.arn
  enable_autoscaling     = var.enable_autoscaling
  desired_count          = var.desired_count
  min_capacity           = var.min_capacity
  max_capacity           = var.max_capacity
  hubble_cpu             = var.hubble_cpu
  hubble_memory          = var.hubble_memory
  app_log_retention_days = var.app_log_retention_days
}

module "demo_pipeline" {
  source = "../../modules/demo_pipeline"

  aws_region                   = var.aws_region
  environment                  = var.environment
  github_repository            = var.github_repository
  github_branch                = var.github_branch
  ecr_repository_name          = aws_ecr_repository.hubble.name
  ecr_repository_arn           = aws_ecr_repository.hubble.arn
  ecs_cluster_name             = module.demo_stack.ecs_cluster_name
  ecs_service_name             = module.demo_stack.ecs_service_name
  codebuild_log_retention_days = var.codebuild_log_retention_days
}
