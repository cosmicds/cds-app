data "aws_caller_identity" "current" {}

resource "random_string" "bucket_suffix" {
  length  = 8
  special = false
  upper   = false
}

resource "aws_ecr_repository" "cds_portal" {
  name                 = var.portal_repository_name
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name        = "${var.environment}-cds-portal-ecr"
    Environment = var.environment
  }
}

resource "aws_ecr_repository" "cds_hubble" {
  name                 = var.hubble_repository_name
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name        = "${var.environment}-cds-hubble-ecr"
    Environment = var.environment
  }
}

resource "aws_s3_bucket" "codepipeline_artifacts" {
  bucket = "${var.environment}-cds-codepipeline-artifacts-${random_string.bucket_suffix.result}"

  tags = {
    Name        = "${var.environment}-codepipeline-artifacts"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_versioning" "codepipeline_artifacts" {
  bucket = aws_s3_bucket.codepipeline_artifacts.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "codepipeline_artifacts" {
  bucket = aws_s3_bucket.codepipeline_artifacts.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "codepipeline_artifacts" {
  bucket = aws_s3_bucket.codepipeline_artifacts.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_iam_role" "codebuild_role" {
  name = "${var.environment}-codebuild-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "codebuild.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "${var.environment}-codebuild-role"
    Environment = var.environment
  }
}

resource "aws_iam_role_policy" "codebuild_policy" {
  name = "${var.environment}-codebuild-policy"
  role = aws_iam_role.codebuild_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetBucketVersioning",
          "s3:GetObject",
          "s3:GetObjectVersion",
          "s3:PutObject"
        ]
        Resource = [
          aws_s3_bucket.codepipeline_artifacts.arn,
          "${aws_s3_bucket.codepipeline_artifacts.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:GetAuthorizationToken",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload",
          "ecr:PutImage"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ecs:UpdateService",
          "ecs:DescribeServices",
          "ecs:RegisterTaskDefinition",
          "ecs:DescribeTaskDefinition"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "iam:PassRole"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role" "codepipeline_role" {
  name = "${var.environment}-codepipeline-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "codepipeline.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "${var.environment}-codepipeline-role"
    Environment = var.environment
  }
}

resource "aws_iam_role_policy" "codepipeline_policy" {
  name = "${var.environment}-codepipeline-policy"
  role = aws_iam_role.codepipeline_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetBucketVersioning",
          "s3:GetObject",
          "s3:GetObjectVersion",
          "s3:PutObject"
        ]
        Resource = [
          aws_s3_bucket.codepipeline_artifacts.arn,
          "${aws_s3_bucket.codepipeline_artifacts.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "codebuild:BatchGetBuilds",
          "codebuild:StartBuild"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "codestar-connections:UseConnection"
        ]
        Resource = aws_codestarconnections_connection.github.arn
      },
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_codestarconnections_connection" "github" {
  name          = "${var.environment}-github-connection"
  provider_type = "GitHub"

  tags = {
    Name        = "${var.environment}-github-connection"
    Environment = var.environment
  }
}

resource "aws_codebuild_project" "cds_portal_build" {
  name         = "${var.environment}-cds-portal-build"
  description  = "Build Docker image for CDS Portal and push with commit-SHA tag"
  service_role = aws_iam_role.codebuild_role.arn

  artifacts {
    type = "CODEPIPELINE"
  }

  environment {
    compute_type                = "BUILD_GENERAL1_SMALL"
    image                       = "aws/codebuild/amazonlinux2-x86_64-standard:3.0"
    type                        = "LINUX_CONTAINER"
    image_pull_credentials_type = "CODEBUILD"
    privileged_mode             = true

    environment_variable {
      name  = "AWS_DEFAULT_REGION"
      value = var.aws_region
    }

    environment_variable {
      name  = "AWS_ACCOUNT_ID"
      value = data.aws_caller_identity.current.account_id
    }

    environment_variable {
      name  = "IMAGE_REPO_NAME"
      value = aws_ecr_repository.cds_portal.name
    }
  }

  source {
    type      = "CODEPIPELINE"
    buildspec = "buildspec-portal.yml"
  }

  tags = {
    Name        = "${var.environment}-cds-portal-build"
    Environment = var.environment
  }
}

resource "aws_codebuild_project" "cds_hubble_build" {
  name         = "${var.environment}-cds-hubble-build"
  description  = "Build Docker image for CDS Hubble and push with commit-SHA tag"
  service_role = aws_iam_role.codebuild_role.arn

  artifacts {
    type = "CODEPIPELINE"
  }

  environment {
    compute_type                = "BUILD_GENERAL1_SMALL"
    image                       = "aws/codebuild/amazonlinux2-x86_64-standard:3.0"
    type                        = "LINUX_CONTAINER"
    image_pull_credentials_type = "CODEBUILD"
    privileged_mode             = true

    environment_variable {
      name  = "AWS_DEFAULT_REGION"
      value = var.aws_region
    }

    environment_variable {
      name  = "AWS_ACCOUNT_ID"
      value = data.aws_caller_identity.current.account_id
    }

    environment_variable {
      name  = "IMAGE_REPO_NAME"
      value = aws_ecr_repository.cds_hubble.name
    }
  }

  source {
    type      = "CODEPIPELINE"
    buildspec = "buildspec-hubble.yml"
  }

  tags = {
    Name        = "${var.environment}-cds-hubble-build"
    Environment = var.environment
  }
}

resource "aws_codebuild_project" "cds_portal_staging_deploy" {
  name         = "${var.environment}-cds-portal-staging-deploy"
  description  = "Deploy CDS Portal to staging ECS service"
  service_role = aws_iam_role.codebuild_role.arn

  artifacts {
    type = "CODEPIPELINE"
  }

  environment {
    compute_type                = "BUILD_GENERAL1_SMALL"
    image                       = "aws/codebuild/amazonlinux2-x86_64-standard:3.0"
    type                        = "LINUX_CONTAINER"
    image_pull_credentials_type = "CODEBUILD"
    privileged_mode             = true

    environment_variable {
      name  = "AWS_DEFAULT_REGION"
      value = var.aws_region
    }

    environment_variable {
      name  = "AWS_ACCOUNT_ID"
      value = data.aws_caller_identity.current.account_id
    }

    environment_variable {
      name  = "IMAGE_REPO_NAME"
      value = aws_ecr_repository.cds_portal.name
    }

    environment_variable {
      name  = "IMAGE_TAG"
      value = "staging"
    }

    environment_variable {
      name  = "ECS_CLUSTER_NAME"
      value = var.staging_cluster_name
    }

    environment_variable {
      name  = "ECS_SERVICE_NAME"
      value = var.staging_portal_service_name
    }
  }

  source {
    type      = "CODEPIPELINE"
    buildspec = "buildspec-deploy.yml"
  }

  tags = {
    Name        = "${var.environment}-cds-portal-staging-deploy"
    Environment = var.environment
    Stage       = "staging"
  }
}

resource "aws_codebuild_project" "cds_hubble_staging_deploy" {
  name         = "${var.environment}-cds-hubble-staging-deploy"
  description  = "Deploy CDS Hubble to staging ECS service"
  service_role = aws_iam_role.codebuild_role.arn

  artifacts {
    type = "CODEPIPELINE"
  }

  environment {
    compute_type                = "BUILD_GENERAL1_SMALL"
    image                       = "aws/codebuild/amazonlinux2-x86_64-standard:3.0"
    type                        = "LINUX_CONTAINER"
    image_pull_credentials_type = "CODEBUILD"
    privileged_mode             = true

    environment_variable {
      name  = "AWS_DEFAULT_REGION"
      value = var.aws_region
    }

    environment_variable {
      name  = "AWS_ACCOUNT_ID"
      value = data.aws_caller_identity.current.account_id
    }

    environment_variable {
      name  = "IMAGE_REPO_NAME"
      value = aws_ecr_repository.cds_hubble.name
    }

    environment_variable {
      name  = "IMAGE_TAG"
      value = "staging"
    }

    environment_variable {
      name  = "ECS_CLUSTER_NAME"
      value = var.staging_cluster_name
    }

    environment_variable {
      name  = "ECS_SERVICE_NAME"
      value = var.staging_hubble_service_name
    }
  }

  source {
    type      = "CODEPIPELINE"
    buildspec = "buildspec-deploy.yml"
  }

  tags = {
    Name        = "${var.environment}-cds-hubble-staging-deploy"
    Environment = var.environment
    Stage       = "staging"
  }
}

resource "aws_codebuild_project" "cds_portal_prod_deploy" {
  name         = "${var.environment}-cds-portal-prod-deploy"
  description  = "Deploy CDS Portal to production ECS service"
  service_role = aws_iam_role.codebuild_role.arn

  artifacts {
    type = "CODEPIPELINE"
  }

  environment {
    compute_type                = "BUILD_GENERAL1_SMALL"
    image                       = "aws/codebuild/amazonlinux2-x86_64-standard:3.0"
    type                        = "LINUX_CONTAINER"
    image_pull_credentials_type = "CODEBUILD"
    privileged_mode             = true

    environment_variable {
      name  = "AWS_DEFAULT_REGION"
      value = var.aws_region
    }

    environment_variable {
      name  = "AWS_ACCOUNT_ID"
      value = data.aws_caller_identity.current.account_id
    }

    environment_variable {
      name  = "IMAGE_REPO_NAME"
      value = aws_ecr_repository.cds_portal.name
    }

    environment_variable {
      name  = "IMAGE_TAG"
      value = "latest"
    }

    environment_variable {
      name  = "ECS_CLUSTER_NAME"
      value = var.production_cluster_name
    }

    environment_variable {
      name  = "ECS_SERVICE_NAME"
      value = var.production_portal_service_name
    }
  }

  source {
    type      = "CODEPIPELINE"
    buildspec = "buildspec-deploy.yml"
  }

  tags = {
    Name        = "${var.environment}-cds-portal-prod-deploy"
    Environment = var.environment
    Stage       = "production"
  }
}

resource "aws_codebuild_project" "cds_hubble_prod_deploy" {
  name         = "${var.environment}-cds-hubble-prod-deploy"
  description  = "Deploy CDS Hubble to production ECS service"
  service_role = aws_iam_role.codebuild_role.arn

  artifacts {
    type = "CODEPIPELINE"
  }

  environment {
    compute_type                = "BUILD_GENERAL1_SMALL"
    image                       = "aws/codebuild/amazonlinux2-x86_64-standard:3.0"
    type                        = "LINUX_CONTAINER"
    image_pull_credentials_type = "CODEBUILD"
    privileged_mode             = true

    environment_variable {
      name  = "AWS_DEFAULT_REGION"
      value = var.aws_region
    }

    environment_variable {
      name  = "AWS_ACCOUNT_ID"
      value = data.aws_caller_identity.current.account_id
    }

    environment_variable {
      name  = "IMAGE_REPO_NAME"
      value = aws_ecr_repository.cds_hubble.name
    }

    environment_variable {
      name  = "IMAGE_TAG"
      value = "latest"
    }

    environment_variable {
      name  = "ECS_CLUSTER_NAME"
      value = var.production_cluster_name
    }

    environment_variable {
      name  = "ECS_SERVICE_NAME"
      value = var.production_hubble_service_name
    }
  }

  source {
    type      = "CODEPIPELINE"
    buildspec = "buildspec-deploy.yml"
  }

  tags = {
    Name        = "${var.environment}-cds-hubble-prod-deploy"
    Environment = var.environment
    Stage       = "production"
  }
}

resource "aws_codepipeline" "cds_pipeline" {
  name     = "${var.environment}-cds-pipeline"
  role_arn = aws_iam_role.codepipeline_role.arn

  artifact_store {
    location = aws_s3_bucket.codepipeline_artifacts.bucket
    type     = "S3"
  }

  stage {
    name = "Source"

    action {
      name             = "Source"
      category         = "Source"
      owner            = "AWS"
      provider         = "CodeStarSourceConnection"
      version          = "1"
      output_artifacts = ["source_output"]

      configuration = {
        ConnectionArn    = aws_codestarconnections_connection.github.arn
        FullRepositoryId = var.github_repository
        BranchName       = var.github_branch
      }
    }
  }

  stage {
    name = "Build"

    action {
      name             = "Build-CDS-Portal"
      category         = "Build"
      owner            = "AWS"
      provider         = "CodeBuild"
      input_artifacts  = ["source_output"]
      output_artifacts = ["portal_build_output"]
      version          = "1"
      run_order        = 1

      configuration = {
        ProjectName = aws_codebuild_project.cds_portal_build.name
      }
    }

    action {
      name             = "Build-CDS-Hubble"
      category         = "Build"
      owner            = "AWS"
      provider         = "CodeBuild"
      input_artifacts  = ["source_output"]
      output_artifacts = ["hubble_build_output"]
      version          = "1"
      run_order        = 1

      configuration = {
        ProjectName = aws_codebuild_project.cds_hubble_build.name
      }
    }
  }

  stage {
    name = "Deploy-Staging"

    action {
      name            = "Deploy-Portal-Staging"
      category        = "Build"
      owner           = "AWS"
      provider        = "CodeBuild"
      input_artifacts = ["portal_build_output"]
      version         = "1"
      run_order       = 1

      configuration = {
        ProjectName = aws_codebuild_project.cds_portal_staging_deploy.name
      }
    }

    action {
      name            = "Deploy-Hubble-Staging"
      category        = "Build"
      owner           = "AWS"
      provider        = "CodeBuild"
      input_artifacts = ["hubble_build_output"]
      version         = "1"
      run_order       = 1

      configuration = {
        ProjectName = aws_codebuild_project.cds_hubble_staging_deploy.name
      }
    }
  }

  stage {
    name = "Approve-Production"

    action {
      name     = "Manual-Approval"
      category = "Approval"
      owner    = "AWS"
      provider = "Manual"
      version  = "1"

      configuration = {
        CustomData      = "Review staging at ${var.staging_portal_url} then approve to deploy to production."
        NotificationArn = var.approval_notification_arn != "" ? var.approval_notification_arn : null
      }
    }
  }

  stage {
    name = "Deploy-Production"

    action {
      name            = "Deploy-Portal-Production"
      category        = "Build"
      owner           = "AWS"
      provider        = "CodeBuild"
      input_artifacts = ["portal_build_output"]
      version         = "1"
      run_order       = 1

      configuration = {
        ProjectName = aws_codebuild_project.cds_portal_prod_deploy.name
      }
    }

    action {
      name            = "Deploy-Hubble-Production"
      category        = "Build"
      owner           = "AWS"
      provider        = "CodeBuild"
      input_artifacts = ["hubble_build_output"]
      version         = "1"
      run_order       = 1

      configuration = {
        ProjectName = aws_codebuild_project.cds_hubble_prod_deploy.name
      }
    }
  }

  tags = {
    Name        = "${var.environment}-cds-pipeline"
    Environment = var.environment
  }
}

resource "aws_cloudwatch_log_group" "codebuild_portal" {
  name              = "/aws/codebuild/${var.environment}-cds-portal-build"
  retention_in_days = var.codebuild_log_retention_days
  log_group_class   = "STANDARD"

  tags = {
    Name        = "${var.environment}-codebuild-portal-logs"
    Environment = var.environment
  }
}

resource "aws_cloudwatch_log_group" "codebuild_hubble" {
  name              = "/aws/codebuild/${var.environment}-cds-hubble-build"
  retention_in_days = var.codebuild_log_retention_days
  log_group_class   = "STANDARD"

  tags = {
    Name        = "${var.environment}-codebuild-hubble-logs"
    Environment = var.environment
  }
}
