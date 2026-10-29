data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_acm_certificate" "site" {
  count = var.site_domain_name == "" ? 0 : 1

  domain      = var.certificate_domain
  statuses    = ["ISSUED"]
  most_recent = true
}

resource "aws_vpc" "main" {
  cidr_block           = "10.20.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name        = "${var.environment}-vpc"
    Environment = var.environment
  }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name        = "${var.environment}-igw"
    Environment = var.environment
  }
}

resource "aws_subnet" "public" {
  count = 2

  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.20.${count.index + 1}.0/24"
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name        = "${var.environment}-public-subnet-${count.index + 1}"
    Environment = var.environment
    Type        = "Public"
  }
}

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

resource "aws_route_table_association" "public" {
  count = 2

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_security_group" "alb" {
  name_prefix = "${var.environment}-alb-"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "HTTP from CloudFront and direct smoke tests"
    from_port   = 80
    to_port     = 80
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
    description     = "Hubble traffic from the ALB"
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

resource "aws_lb" "main" {
  name               = "${var.environment}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id
  idle_timeout       = 120

  enable_deletion_protection = false

  tags = {
    Name        = "${var.environment}-alb"
    Environment = var.environment
  }
}

resource "aws_lb_target_group" "hubble" {
  name        = "${var.environment}-cds-hubble-tg"
  port        = 8765
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200,307"
    path                = "/"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 10
    unhealthy_threshold = 3
  }

  tags = {
    Name        = "${var.environment}-cds-hubble-tg"
    Environment = var.environment
  }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.hubble.arn
  }

  tags = {
    Name        = "${var.environment}-http-listener"
    Environment = var.environment
  }
}

resource "aws_cloudfront_distribution" "demo" {
  enabled         = true
  is_ipv6_enabled = true
  comment         = "${var.environment} CloudFront distribution for the Hubble demo"
  price_class     = "PriceClass_100"
  aliases         = var.site_domain_name == "" ? [] : [var.site_domain_name]

  origin {
    domain_name = aws_lb.main.dns_name
    origin_id   = "alb-${aws_lb.main.id}"

    custom_origin_config {
      http_port                = 80
      https_port               = 443
      origin_protocol_policy   = "http-only"
      origin_ssl_protocols     = ["TLSv1.2"]
      origin_keepalive_timeout = 60
      origin_read_timeout      = 60
    }
  }

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

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = var.site_domain_name == "" ? true : null
    acm_certificate_arn            = var.site_domain_name == "" ? null : data.aws_acm_certificate.site[0].arn
    ssl_support_method             = var.site_domain_name == "" ? null : "sni-only"
    minimum_protocol_version       = var.site_domain_name == "" ? "TLSv1" : "TLSv1.2_2021"
  }

  tags = {
    Name        = "${var.environment}-cloudfront"
    Environment = var.environment
  }
}

resource "aws_ecs_cluster" "main" {
  name = "${var.environment}-cluster"

  setting {
    name  = "containerInsights"
    value = "disabled"
  }

  tags = {
    Name        = "${var.environment}-ecs-cluster"
    Environment = var.environment
  }
}

resource "aws_iam_role" "ecs_task_execution" {
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

resource "aws_iam_role_policy_attachment" "ecs_task_execution" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "ecs_secrets" {
  name = "${var.environment}-ecs-secrets-policy"
  role = aws_iam_role.ecs_task_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = [var.hubble_secret_arn]
      }
    ]
  })
}

resource "aws_cloudwatch_log_group" "hubble" {
  name              = "/ecs/${var.environment}-cds-hubble"
  retention_in_days = var.app_log_retention_days
  log_group_class   = "STANDARD"

  tags = {
    Name        = "${var.environment}-cds-hubble-logs"
    Environment = var.environment
  }
}

resource "aws_ecs_task_definition" "hubble" {
  family                   = "${var.environment}-cds-hubble"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.hubble_cpu
  memory                   = var.hubble_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn

  container_definitions = jsonencode([
    {
      name  = "cds-hubble"
      image = var.cds_hubble_image
      portMappings = [
        {
          containerPort = 8765
          protocol      = "tcp"
        }
      ]
      essential = true
      environment = [
        for key, value in var.hubble_environment_vars : {
          name  = key
          value = value
        }
      ]
      secrets = [
        for secret_name in var.hubble_secret_names : {
          name      = secret_name
          valueFrom = "${var.hubble_secret_arn}:${secret_name}::"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.hubble.name
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

resource "aws_ecs_service" "hubble" {
  name                               = "${var.environment}-cds-hubble"
  cluster                            = aws_ecs_cluster.main.id
  task_definition                    = aws_ecs_task_definition.hubble.arn
  desired_count                      = var.enable_autoscaling ? var.min_capacity : var.desired_count
  launch_type                        = "FARGATE"
  deployment_minimum_healthy_percent = 0
  deployment_maximum_percent         = 100
  health_check_grace_period_seconds  = 120
  wait_for_steady_state              = false

  network_configuration {
    security_groups  = [aws_security_group.ecs_tasks.id]
    subnets          = aws_subnet.public[*].id
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.hubble.arn
    container_name   = "cds-hubble"
    container_port   = 8765
  }

  depends_on = [aws_lb_listener.http]

  tags = {
    Name        = "${var.environment}-cds-hubble-service"
    Environment = var.environment
  }
}

resource "aws_appautoscaling_target" "hubble" {
  count = var.enable_autoscaling ? 1 : 0

  max_capacity       = var.max_capacity
  min_capacity       = var.min_capacity
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.hubble.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"

  tags = {
    Name        = "${var.environment}-cds-hubble-autoscaling-target"
    Environment = var.environment
  }
}

resource "aws_appautoscaling_policy" "hubble_cpu" {
  count = var.enable_autoscaling ? 1 : 0

  name               = "${var.environment}-cds-hubble-cpu-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.hubble[0].resource_id
  scalable_dimension = aws_appautoscaling_target.hubble[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.hubble[0].service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }

    target_value       = var.autoscaling_cpu_target
    scale_in_cooldown  = 300
    scale_out_cooldown = 120
  }
}

resource "aws_appautoscaling_policy" "hubble_requests" {
  count = var.enable_autoscaling ? 1 : 0

  name               = "${var.environment}-cds-hubble-request-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.hubble[0].resource_id
  scalable_dimension = aws_appautoscaling_target.hubble[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.hubble[0].service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ALBRequestCountPerTarget"
      resource_label         = "${aws_lb.main.arn_suffix}/${aws_lb_target_group.hubble.arn_suffix}"
    }

    target_value       = var.autoscaling_requests_per_target
    scale_in_cooldown  = 300
    scale_out_cooldown = 120
  }
}
