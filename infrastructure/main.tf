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

# Data sources
data "aws_availability_zones" "available" {
  state = "available"
}

# VPC
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name        = "${var.environment}-vpc"
    Environment = var.environment
  }
}

# Internet Gateway
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name        = "${var.environment}-igw"
    Environment = var.environment
  }
}

# Public Subnets
resource "aws_subnet" "public" {
  count = 2

  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.${count.index + 1}.0/24"
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name        = "${var.environment}-public-subnet-${count.index + 1}"
    Environment = var.environment
    Type        = "Public"
  }
}

# Private Subnets
resource "aws_subnet" "private" {
  count = 2

  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.${count.index + 10}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name        = "${var.environment}-private-subnet-${count.index + 1}"
    Environment = var.environment
    Type        = "Private"
  }
}

# NAT Gateways
resource "aws_eip" "nat" {
  count = 2

  domain = "vpc"
  depends_on = [aws_internet_gateway.main]

  tags = {
    Name        = "${var.environment}-nat-eip-${count.index + 1}"
    Environment = var.environment
  }
}

resource "aws_nat_gateway" "main" {
  count = 2

  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id

  tags = {
    Name        = "${var.environment}-nat-gateway-${count.index + 1}"
    Environment = var.environment
  }

  depends_on = [aws_internet_gateway.main]
}

# Route Tables
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = {
    Name        = "${var.environment}-public-rt"
    Environment = var.environment
  }
}

resource "aws_route_table" "private" {
  count = 2

  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main[count.index].id
  }

  tags = {
    Name        = "${var.environment}-private-rt-${count.index + 1}"
    Environment = var.environment
  }
}

# Route Table Associations
resource "aws_route_table_association" "public" {
  count = 2

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "private" {
  count = 2

  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[count.index].id
}

# Security Groups
resource "aws_security_group" "alb" {
  name_prefix = "${var.environment}-alb-"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "HTTP from CloudFront and direct access"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS from CloudFront and direct access"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.environment}-alb-sg"
    Environment = var.environment
  }
}

resource "aws_security_group" "ecs_tasks" {
  name_prefix = "${var.environment}-ecs-tasks-"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "CDS Portal from ALB"
    from_port       = 8865
    to_port         = 8865
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  ingress {
    description     = "CDS Hubble from ALB"
    from_port       = 8765
    to_port         = 8765
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.environment}-ecs-tasks-sg"
    Environment = var.environment
  }
}

# Application Load Balancer
resource "aws_lb" "main" {
  name               = "${var.environment}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id

  enable_deletion_protection = false

  tags = {
    Name        = "${var.environment}-alb"
    Environment = var.environment
  }
}

# Target Groups
resource "aws_lb_target_group" "cds_portal" {
  name        = "${var.environment}-cds-portal-tg"
  port        = 8865
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 60
    matcher             = "200"
    path                = "/"
    port                = "8865"
    protocol            = "HTTP"
    timeout             = 30
    unhealthy_threshold = 2
  }

  tags = {
    Name        = "${var.environment}-cds-portal-tg"
    Environment = var.environment
  }
}

resource "aws_lb_target_group" "cds_hubble" {
  name        = "${var.environment}-cds-hubble-tg"
  port        = 8765
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 60
    matcher             = "200,307"
    path                = "/hubbles-law"
    port                = "8765"
    protocol            = "HTTP"
    timeout             = 30
    unhealthy_threshold = 2
  }

  tags = {
    Name        = "${var.environment}-cds-hubble-tg"
    Environment = var.environment
  }
}

# Load Balancer Listener
resource "aws_lb_listener" "main" {
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.cds_portal.arn
  }

  tags = {
    Name        = "${var.environment}-listener"
    Environment = var.environment
  }
}

# Listener Rules
resource "aws_lb_listener_rule" "cds_hubble" {
  listener_arn = aws_lb_listener.main.arn
  priority     = 100

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.cds_hubble.arn
  }

  condition {
    path_pattern {
      values = ["/hubbles-law*"]
    }
  }

  tags = {
    Name        = "${var.environment}-hubble-rule"
    Environment = var.environment
  }
}

# ACM Certificate for ALB (using existing imported certificate)
data "aws_acm_certificate" "alb" {
  domain   = var.alb_domain_name
  statuses = ["ISSUED"]
}

# HTTPS Listener
resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.main.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = data.aws_acm_certificate.alb.arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.cds_portal.arn
  }

  tags = {
    Name        = "${var.environment}-https-listener"
    Environment = var.environment
  }
}

# HTTPS Listener Rule for Hubble
resource "aws_lb_listener_rule" "cds_hubble_https" {
  listener_arn = aws_lb_listener.https.arn
  priority     = 100

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.cds_hubble.arn
  }

  condition {
    path_pattern {
      values = ["/hubbles-law*"]
    }
  }

  tags = {
    Name        = "${var.environment}-hubble-https-rule"
    Environment = var.environment
  }
}

# CloudFront Origin Access Control for ALB
resource "aws_cloudfront_origin_access_control" "alb" {
  name                              = "${var.environment}-alb-oac"
  description                       = "Origin Access Control for ALB"
  origin_access_control_origin_type = "mediapackagev2"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# CloudFront Distribution
resource "aws_cloudfront_distribution" "apps" {
  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = ""
  comment             = "${var.environment} CloudFront distribution for CDS applications"
  price_class         = "PriceClass_100"
  aliases             = [var.alb_domain_name]

  origin {
    domain_name = aws_lb.main.dns_name
    origin_id   = "alb-${aws_lb.main.id}"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]

      origin_keepalive_timeout = 60
      origin_read_timeout      = 60
    }

    custom_header {
      name  = "X-CloudFront-Secret"
      value = local.cloudfront_secret
    }
  }

  # Default cache behavior for CDS Portal
  default_cache_behavior {
    allowed_methods  = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods   = ["GET", "HEAD", "OPTIONS"]
    target_origin_id = "alb-${aws_lb.main.id}"

    forwarded_values {
      query_string = true
      headers      = ["*"]

      cookies {
        forward = "all"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 0
    max_ttl                = 0
    compress               = true
  }

  # Cache behavior for CDS Hubble
  ordered_cache_behavior {
    path_pattern     = "/hubbles-law*"
    allowed_methods  = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods   = ["GET", "HEAD", "OPTIONS"]
    target_origin_id = "alb-${aws_lb.main.id}"

    forwarded_values {
      query_string = true
      headers      = ["*"]

      cookies {
        forward = "all"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 0
    max_ttl                = 0
    compress               = true
  }

  # Cache behavior for static assets (if any)
  ordered_cache_behavior {
    path_pattern     = "/static/*"
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD", "OPTIONS"]
    target_origin_id = "alb-${aws_lb.main.id}"

    forwarded_values {
      query_string = true
      headers      = ["*"]

      cookies {
        forward = "all"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 3600
    max_ttl                = 86400
    compress               = true
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    acm_certificate_arn      = data.aws_acm_certificate.alb.arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }

  tags = {
    Name        = "${var.environment}-cloudfront"
    Environment = var.environment
  }
}

# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "${var.environment}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Name        = "${var.environment}-ecs-cluster"
    Environment = var.environment
  }
}

# Secrets Manager for sensitive environment variables
resource "aws_secretsmanager_secret" "cds_portal_secrets" {
  name        = "${var.environment}/cds-portal/secrets"
  description = "Secrets for CDS Portal application"

  tags = {
    Name        = "${var.environment}-cds-portal-secrets"
    Environment = var.environment
  }
}

resource "aws_secretsmanager_secret" "cds_hubble_secrets" {
  name        = "${var.environment}/cds-hubble/secrets"
  description = "Secrets for CDS Hubble application"

  tags = {
    Name        = "${var.environment}-cds-hubble-secrets"
    Environment = var.environment
  }
}

# Parameter Store for non-sensitive environment variables
resource "aws_ssm_parameter" "cds_portal_env_vars" {
  for_each = {
    "NODE_ENV"    = "production"
    "LOG_LEVEL"   = "info"
  }

  name  = "/${var.environment}/cds-portal/env/${each.key}"
  type  = "String"
  value = each.value

  tags = {
    Name        = "${var.environment}-cds-portal-${each.key}"
    Environment = var.environment
    Application = "cds-portal"
  }
}

resource "aws_ssm_parameter" "cds_hubble_env_vars" {
  for_each = {
    "NODE_ENV"    = "production"
    "LOG_LEVEL"   = "info"
  }

  name  = "/${var.environment}/cds-hubble/env/${each.key}"
  type  = "String"
  value = each.value

  tags = {
    Name        = "${var.environment}-cds-hubble-${each.key}"
    Environment = var.environment
    Application = "cds-hubble"
  }
}

# ECS Task Execution Role
resource "aws_iam_role" "ecs_task_execution_role" {
  name = "${var.environment}-ecs-task-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "${var.environment}-ecs-task-execution-role"
    Environment = var.environment
  }
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_role_policy" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Additional policy for accessing Secrets Manager and Parameter Store
resource "aws_iam_role_policy" "ecs_secrets_policy" {
  name = "${var.environment}-ecs-secrets-policy"
  role = aws_iam_role.ecs_task_execution_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          aws_secretsmanager_secret.cds_portal_secrets.arn,
          aws_secretsmanager_secret.cds_hubble_secrets.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameters",
          "ssm:GetParameter"
        ]
        Resource = [
          "arn:aws:ssm:${var.aws_region}:*:parameter/${var.environment}/cds-portal/env/*",
          "arn:aws:ssm:${var.aws_region}:*:parameter/${var.environment}/cds-hubble/env/*"
        ]
      }
    ]
  })
}

# ECS Task Definitions
resource "aws_ecs_task_definition" "cds_portal" {
  family                   = "${var.environment}-cds-portal"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn

  container_definitions = jsonencode([
    {
      name  = "cds-portal"
      image = "${aws_ecr_repository.cds_portal.repository_url}:latest"
      portMappings = [
        {
          containerPort = 8865
          protocol      = "tcp"
        }
      ]
      essential = true

      environment = [
        {
          name  = "NODE_ENV"
          value = "production"
        }
      ]

      secrets = [
        {
          name      = "SOLARA_SESSION_SECRET_KEY"
          valueFrom = "${aws_secretsmanager_secret.cds_portal_secrets.arn}:SOLARA_SESSION_SECRET_KEY::"
        },
        {
          name      = "SOLARA_OAUTH_CLIENT_ID"
          valueFrom = "${aws_secretsmanager_secret.cds_portal_secrets.arn}:SOLARA_OAUTH_CLIENT_ID::"
        },
        {
          name      = "SOLARA_OAUTH_CLIENT_SECRET"
          valueFrom = "${aws_secretsmanager_secret.cds_portal_secrets.arn}:SOLARA_OAUTH_CLIENT_SECRET::"
        },
        {
          name      = "SOLARA_OAUTH_API_BASE_URL"
          valueFrom = "${aws_secretsmanager_secret.cds_portal_secrets.arn}:SOLARA_OAUTH_API_BASE_URL::"
        },
        {
          name      = "SOLARA_OAUTH_SCOPE"
          valueFrom = "${aws_secretsmanager_secret.cds_portal_secrets.arn}:SOLARA_OAUTH_SCOPE::"
        },
        {
          name      = "SOLARA_SESSION_HTTPS_ONLY"
          valueFrom = "${aws_secretsmanager_secret.cds_portal_secrets.arn}:SOLARA_SESSION_HTTPS_ONLY::"
        },
        {
          name      = "CDS_API_KEY"
          valueFrom = "${aws_secretsmanager_secret.cds_portal_secrets.arn}:CDS_API_KEY::"
        },
        {
          name      = "SOLARA_APP"
          valueFrom = "${aws_secretsmanager_secret.cds_portal_secrets.arn}:SOLARA_APP::"
        },
        {
          name      = "SOLARA_BASE_URL"
          valueFrom = "${aws_secretsmanager_secret.cds_portal_secrets.arn}:SOLARA_BASE_URL::"
        },
        {
          name      = "AWS_EBS_URL"
          valueFrom = "${aws_secretsmanager_secret.cds_portal_secrets.arn}:AWS_EBS_URL::"
        },
        {
          name      = "EMAIL_PASSWORD"
          valueFrom = "${aws_secretsmanager_secret.cds_portal_secrets.arn}:EMAIL_PASSWORD::"
        },
        {
          name      = "EMAIL_SERVICE"
          valueFrom = "${aws_secretsmanager_secret.cds_portal_secrets.arn}:EMAIL_SERVICE::"
        },
        {
          name      = "EMAIL_USERNAME"
          valueFrom = "${aws_secretsmanager_secret.cds_portal_secrets.arn}:EMAIL_USERNAME::"
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.cds_portal.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])

  tags = {
    Name        = "${var.environment}-cds-portal-task"
    Environment = var.environment
  }
}

resource "aws_ecs_task_definition" "cds_hubble" {
  family                   = "${var.environment}-cds-hubble"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 1024
  memory                   = 2048
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn

  container_definitions = jsonencode([
    {
      name  = "cds-hubble"
      image = "${aws_ecr_repository.cds_hubble.repository_url}:latest"
      portMappings = [
        {
          containerPort = 8765
          protocol      = "tcp"
        }
      ]
      essential = true

      environment = [
        {
          name  = "NODE_ENV"
          value = "production"
        }
      ]

      secrets = [
        {
          name      = "SOLARA_SESSION_SECRET_KEY"
          valueFrom = "${aws_secretsmanager_secret.cds_hubble_secrets.arn}:SOLARA_SESSION_SECRET_KEY::"
        },
        {
          name      = "SOLARA_OAUTH_CLIENT_ID"
          valueFrom = "${aws_secretsmanager_secret.cds_hubble_secrets.arn}:SOLARA_OAUTH_CLIENT_ID::"
        },
        {
          name      = "SOLARA_OAUTH_CLIENT_SECRET"
          valueFrom = "${aws_secretsmanager_secret.cds_hubble_secrets.arn}:SOLARA_OAUTH_CLIENT_SECRET::"
        },
        {
          name      = "SOLARA_OAUTH_API_BASE_URL"
          valueFrom = "${aws_secretsmanager_secret.cds_hubble_secrets.arn}:SOLARA_OAUTH_API_BASE_URL::"
        },
        {
          name      = "SOLARA_OAUTH_SCOPE"
          valueFrom = "${aws_secretsmanager_secret.cds_hubble_secrets.arn}:SOLARA_OAUTH_SCOPE::"
        },
        {
          name      = "SOLARA_SESSION_HTTPS_ONLY"
          valueFrom = "${aws_secretsmanager_secret.cds_hubble_secrets.arn}:SOLARA_SESSION_HTTPS_ONLY::"
        },
        {
          name      = "CDS_API_KEY"
          valueFrom = "${aws_secretsmanager_secret.cds_hubble_secrets.arn}:CDS_API_KEY::"
        },
        {
          name      = "SOLARA_OAUTH_PRIVATE"
          valueFrom = "${aws_secretsmanager_secret.cds_hubble_secrets.arn}:SOLARA_OAUTH_PRIVATE::"
        },
        {
          name      = "SOLARA_APP"
          valueFrom = "${aws_secretsmanager_secret.cds_hubble_secrets.arn}:SOLARA_APP::"
        },
        {
          name      = "SOLARA_ROOT_PATH"
          valueFrom = "${aws_secretsmanager_secret.cds_hubble_secrets.arn}:SOLARA_ROOT_PATH::"
        },
        {
          name      = "SOLARA_BASE_URL"
          valueFrom = "${aws_secretsmanager_secret.cds_hubble_secrets.arn}:SOLARA_BASE_URL::"
        },
        {
          name      = "CDS_SHOW_TEAM_INTERFACE"
          valueFrom = "${aws_secretsmanager_secret.cds_hubble_secrets.arn}:CDS_SHOW_TEAM_INTERFACE::"
        },
        {
          name      = "GOOGLE_ANALYTICS_TAG"
          valueFrom = "${aws_secretsmanager_secret.cds_hubble_secrets.arn}:GOOGLE_ANALYTICS_TAG::"
        },
        {
          name      = "AWS_EBS_URL"
          valueFrom = "${aws_secretsmanager_secret.cds_hubble_secrets.arn}:AWS_EBS_URL::"
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.cds_hubble.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])

  tags = {
    Name        = "${var.environment}-cds-hubble-task"
    Environment = var.environment
  }
}

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "cds_portal" {
  name              = "/ecs/${var.environment}-cds-portal"
  retention_in_days = 7

  tags = {
    Name        = "${var.environment}-cds-portal-logs"
    Environment = var.environment
  }
}

resource "aws_cloudwatch_log_group" "cds_hubble" {
  name              = "/ecs/${var.environment}-cds-hubble"
  retention_in_days = 7

  tags = {
    Name        = "${var.environment}-cds-hubble-logs"
    Environment = var.environment
  }
}

# ECS Services
resource "aws_ecs_service" "cds_portal" {
  name            = "${var.environment}-cds-portal"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.cds_portal.arn
  desired_count   = var.cds_portal_min_capacity
  launch_type     = "FARGATE"

  network_configuration {
    security_groups  = [aws_security_group.ecs_tasks.id]
    subnets          = aws_subnet.private[*].id
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.cds_portal.arn
    container_name   = "cds-portal"
    container_port   = 8865
  }

  depends_on = [aws_lb_listener.main]

  tags = {
    Name        = "${var.environment}-cds-portal-service"
    Environment = var.environment
  }
}

resource "aws_ecs_service" "cds_hubble" {
  name            = "${var.environment}-cds-hubble"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.cds_hubble.arn
  desired_count   = var.cds_hubble_min_capacity
  launch_type     = "FARGATE"

  network_configuration {
    security_groups  = [aws_security_group.ecs_tasks.id]
    subnets          = aws_subnet.private[*].id
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.cds_hubble.arn
    container_name   = "cds-hubble"
    container_port   = 8765
  }

  depends_on = [aws_lb_listener.main]

  tags = {
    Name        = "${var.environment}-cds-hubble-service"
    Environment = var.environment
  }
}

# Auto Scaling Resources
resource "aws_appautoscaling_target" "cds_portal" {
  max_capacity       = var.cds_portal_max_capacity
  min_capacity       = var.cds_portal_min_capacity
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.cds_portal.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"

  tags = {
    Name        = "${var.environment}-cds-portal-autoscaling-target"
    Environment = var.environment
  }
}

resource "aws_appautoscaling_target" "cds_hubble" {
  max_capacity       = var.cds_hubble_max_capacity
  min_capacity       = var.cds_hubble_min_capacity
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.cds_hubble.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"

  tags = {
    Name        = "${var.environment}-cds-hubble-autoscaling-target"
    Environment = var.environment
  }
}

# Auto Scaling Policies - CPU Based
resource "aws_appautoscaling_policy" "cds_portal_cpu" {
  name               = "${var.environment}-cds-portal-cpu-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.cds_portal.resource_id
  scalable_dimension = aws_appautoscaling_target.cds_portal.scalable_dimension
  service_namespace  = aws_appautoscaling_target.cds_portal.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value       = 70.0
    scale_in_cooldown  = 300
    scale_out_cooldown = 300
  }
}

resource "aws_appautoscaling_policy" "cds_hubble_cpu" {
  name               = "${var.environment}-cds-hubble-cpu-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.cds_hubble.resource_id
  scalable_dimension = aws_appautoscaling_target.cds_hubble.scalable_dimension
  service_namespace  = aws_appautoscaling_target.cds_hubble.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value       = 70.0
    scale_in_cooldown  = 300
    scale_out_cooldown = 300
  }
}

# Generate a random secret for CloudFront
resource "random_password" "cloudfront_secret" {
  count   = var.cloudfront_secret == "" ? 1 : 0
  length  = 32
  special = true
}

# Store the secret in Parameter Store for reference
resource "aws_ssm_parameter" "cloudfront_secret" {
  name  = "/${var.environment}/cloudfront/secret"
  type  = "SecureString"
  value = var.cloudfront_secret != "" ? var.cloudfront_secret : random_password.cloudfront_secret[0].result

  tags = {
    Name        = "${var.environment}-cloudfront-secret"
    Environment = var.environment
  }
}

# Use the secret in CloudFront
locals {
  cloudfront_secret = var.cloudfront_secret != "" ? var.cloudfront_secret : random_password.cloudfront_secret[0].result
}