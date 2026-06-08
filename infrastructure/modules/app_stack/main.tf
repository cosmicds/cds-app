data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_acm_certificate" "site" {
  domain      = var.certificate_domain
  statuses    = ["ISSUED"]
  most_recent = true
}

resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
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
  cidr_block              = "10.0.${count.index + 1}.0/24"
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name        = "${var.environment}-public-subnet-${count.index + 1}"
    Environment = var.environment
    Type        = "Public"
  }
}

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

resource "aws_eip" "nat" {
  count = var.create_private_nat_gateways ? 2 : 0

  domain = "vpc"

  depends_on = [aws_internet_gateway.main]

  tags = {
    Name        = "${var.environment}-nat-eip-${count.index + 1}"
    Environment = var.environment
  }
}

resource "aws_nat_gateway" "main" {
  count = var.create_private_nat_gateways ? 2 : 0

  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id

  depends_on = [aws_internet_gateway.main]

  tags = {
    Name        = "${var.environment}-nat-gateway-${count.index + 1}"
    Environment = var.environment
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

resource "aws_route_table" "private" {
  count = var.create_private_nat_gateways ? 2 : 0

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

resource "aws_route_table_association" "public" {
  count = 2

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "private" {
  count = var.create_private_nat_gateways ? 2 : 0

  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[count.index].id
}

resource "aws_security_group" "alb" {
  name_prefix = "${var.environment}-alb-"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS"
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

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type = "redirect"

    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }

  tags = {
    Name        = "${var.environment}-http-listener"
    Environment = var.environment
  }
}

resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.main.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = data.aws_acm_certificate.site.arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.cds_portal.arn
  }

  tags = {
    Name        = "${var.environment}-https-listener"
    Environment = var.environment
  }
}

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

resource "aws_cloudfront_distribution" "apps" {
  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = ""
  comment             = "${var.environment} CloudFront distribution for CDS applications"
  price_class         = "PriceClass_100"
  aliases             = [var.site_domain_name]

  origin {
    domain_name = aws_lb.main.dns_name
    origin_id   = "alb-${aws_lb.main.id}"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = var.cloudfront_origin_protocol_policy
      origin_ssl_protocols   = ["TLSv1.2"]

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
    acm_certificate_arn      = data.aws_acm_certificate.site.arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
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
    value = var.enable_container_insights ? "enabled" : "disabled"
  }

  tags = {
    Name        = "${var.environment}-ecs-cluster"
    Environment = var.environment
  }
}

locals {
  service_subnet_ids = var.use_private_service_subnets ? aws_subnet.private[*].id : aws_subnet.public[*].id
  assign_public_ip   = var.use_private_service_subnets ? false : true
}

resource "aws_ecs_cluster_capacity_providers" "main" {
  count = var.enable_cluster_capacity_providers ? 1 : 0

  cluster_name       = aws_ecs_cluster.main.name
  capacity_providers = ["FARGATE", "FARGATE_SPOT"]

  default_capacity_provider_strategy {
    capacity_provider = "FARGATE"
    base              = 1
    weight            = 1
  }
}

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

data "aws_secretsmanager_secret_version" "portal_source" {
  count     = var.portal_secret_source_arn != null ? 1 : 0
  secret_id = var.portal_secret_source_arn
}

data "aws_secretsmanager_secret_version" "hubble_source" {
  count     = var.hubble_secret_source_arn != null ? 1 : 0
  secret_id = var.hubble_secret_source_arn
}

resource "aws_secretsmanager_secret_version" "cds_portal_seed" {
  count         = var.portal_secret_source_arn != null ? 1 : 0
  secret_id     = aws_secretsmanager_secret.cds_portal_secrets.id
  secret_string = data.aws_secretsmanager_secret_version.portal_source[0].secret_string
}

resource "aws_secretsmanager_secret_version" "cds_hubble_seed" {
  count         = var.hubble_secret_source_arn != null ? 1 : 0
  secret_id     = aws_secretsmanager_secret.cds_hubble_secrets.id
  secret_string = data.aws_secretsmanager_secret_version.hubble_source[0].secret_string
}

resource "aws_ssm_parameter" "cds_portal_env_vars" {
  for_each = var.portal_environment_vars

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
  for_each = var.hubble_environment_vars

  name  = "/${var.environment}/cds-hubble/env/${each.key}"
  type  = "String"
  value = each.value

  tags = {
    Name        = "${var.environment}-cds-hubble-${each.key}"
    Environment = var.environment
    Application = "cds-hubble"
  }
}

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

resource "aws_cloudwatch_log_group" "cds_portal" {
  name              = "/ecs/${var.environment}-cds-portal"
  retention_in_days = var.app_log_retention_days
  log_group_class   = var.log_group_class

  tags = {
    Name        = "${var.environment}-cds-portal-logs"
    Environment = var.environment
  }
}

resource "aws_cloudwatch_log_group" "cds_hubble" {
  name              = "/ecs/${var.environment}-cds-hubble"
  retention_in_days = var.app_log_retention_days
  log_group_class   = var.log_group_class

  tags = {
    Name        = "${var.environment}-cds-hubble-logs"
    Environment = var.environment
  }
}

resource "aws_ecs_task_definition" "cds_portal" {
  family                   = "${var.environment}-cds-portal"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.cds_portal_cpu
  memory                   = var.cds_portal_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn

  container_definitions = jsonencode([
    {
      name  = "cds-portal"
      image = var.cds_portal_image
      portMappings = [
        {
          containerPort = 8865
          protocol      = "tcp"
        }
      ]
      essential = true
      environment = [
        for key, value in var.portal_environment_vars : {
          name  = key
          value = value
        }
      ]
      secrets = [
        for secret_name in var.portal_secret_names : {
          name      = secret_name
          valueFrom = "${aws_secretsmanager_secret.cds_portal_secrets.arn}:${secret_name}::"
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
  cpu                      = var.cds_hubble_cpu
  memory                   = var.cds_hubble_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn

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
          valueFrom = "${aws_secretsmanager_secret.cds_hubble_secrets.arn}:${secret_name}::"
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

resource "aws_ecs_service" "cds_portal" {
  name            = "${var.environment}-cds-portal"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.cds_portal.arn
  desired_count   = var.cds_portal_min_capacity
  launch_type     = var.use_capacity_provider_strategy ? null : "FARGATE"

  dynamic "capacity_provider_strategy" {
    for_each = var.use_capacity_provider_strategy ? [
      {
        capacity_provider = "FARGATE"
        base              = 1
        weight            = 1
      },
      {
        capacity_provider = "FARGATE_SPOT"
        base              = 0
        weight            = 4
      }
    ] : []

    content {
      capacity_provider = capacity_provider_strategy.value.capacity_provider
      base              = capacity_provider_strategy.value.base
      weight            = capacity_provider_strategy.value.weight
    }
  }

  network_configuration {
    security_groups  = [aws_security_group.ecs_tasks.id]
    subnets          = local.service_subnet_ids
    assign_public_ip = local.assign_public_ip
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.cds_portal.arn
    container_name   = "cds-portal"
    container_port   = 8865
  }

  depends_on = [aws_lb_listener.https]

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
  launch_type     = var.use_capacity_provider_strategy ? null : "FARGATE"

  dynamic "capacity_provider_strategy" {
    for_each = var.use_capacity_provider_strategy ? [
      {
        capacity_provider = "FARGATE"
        base              = 1
        weight            = 1
      },
      {
        capacity_provider = "FARGATE_SPOT"
        base              = 0
        weight            = 4
      }
    ] : []

    content {
      capacity_provider = capacity_provider_strategy.value.capacity_provider
      base              = capacity_provider_strategy.value.base
      weight            = capacity_provider_strategy.value.weight
    }
  }

  network_configuration {
    security_groups  = [aws_security_group.ecs_tasks.id]
    subnets          = local.service_subnet_ids
    assign_public_ip = local.assign_public_ip
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.cds_hubble.arn
    container_name   = "cds-hubble"
    container_port   = 8765
  }

  depends_on = [aws_lb_listener.https]

  tags = {
    Name        = "${var.environment}-cds-hubble-service"
    Environment = var.environment
  }
}

resource "aws_appautoscaling_target" "cds_portal" {
  count = var.enable_autoscaling ? 1 : 0

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
  count = var.enable_autoscaling ? 1 : 0

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

resource "aws_appautoscaling_policy" "cds_portal_cpu" {
  count = var.enable_autoscaling ? 1 : 0

  name               = "${var.environment}-cds-portal-cpu-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.cds_portal[0].resource_id
  scalable_dimension = aws_appautoscaling_target.cds_portal[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.cds_portal[0].service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value       = 70.0
    scale_in_cooldown  = 300
    scale_out_cooldown = 300
  }
}

resource "aws_appautoscaling_policy" "cds_portal_requests" {
  count = var.enable_autoscaling ? 1 : 0

  name               = "${var.environment}-cds-portal-request-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.cds_portal[0].resource_id
  scalable_dimension = aws_appautoscaling_target.cds_portal[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.cds_portal[0].service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ALBRequestCountPerTarget"
      resource_label         = "${aws_lb.main.arn_suffix}/${aws_lb_target_group.cds_portal.arn_suffix}"
    }
    target_value       = 500
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}

resource "aws_appautoscaling_policy" "cds_hubble_cpu" {
  count = var.enable_autoscaling ? 1 : 0

  name               = "${var.environment}-cds-hubble-cpu-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.cds_hubble[0].resource_id
  scalable_dimension = aws_appautoscaling_target.cds_hubble[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.cds_hubble[0].service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value       = 70.0
    scale_in_cooldown  = 300
    scale_out_cooldown = 300
  }
}

resource "aws_appautoscaling_policy" "cds_hubble_requests" {
  count = var.enable_autoscaling ? 1 : 0

  name               = "${var.environment}-cds-hubble-request-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.cds_hubble[0].resource_id
  scalable_dimension = aws_appautoscaling_target.cds_hubble[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.cds_hubble[0].service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ALBRequestCountPerTarget"
      resource_label         = "${aws_lb.main.arn_suffix}/${aws_lb_target_group.cds_hubble.arn_suffix}"
    }
    target_value       = 500
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}
