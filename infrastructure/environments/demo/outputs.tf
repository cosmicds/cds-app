output "site_url" {
  description = "Active URL for the demo environment"
  value       = module.demo_stack.site_url
}

output "cloudfront_domain_name" {
  description = "CloudFront hostname used before the custom DNS cutover"
  value       = module.demo_stack.cloudfront_domain_name
}

output "alb_dns_name" {
  description = "DNS name of the demo ALB"
  value       = module.demo_stack.alb_dns_name
}

output "ecs_cluster_name" {
  description = "Name of the demo ECS cluster"
  value       = module.demo_stack.ecs_cluster_name
}

output "ecs_service_name" {
  description = "Name of the demo Hubble ECS service"
  value       = module.demo_stack.ecs_service_name
}

output "ecr_repository_url" {
  description = "URL of the isolated demo Hubble ECR repository"
  value       = aws_ecr_repository.hubble.repository_url
}

output "hubble_secret_arn" {
  description = "ARN of the manually populated demo Hubble secret"
  value       = aws_secretsmanager_secret.hubble.arn
}

output "codepipeline_name" {
  description = "Name of the demo-only CodePipeline"
  value       = module.demo_pipeline.codepipeline_name
}

output "github_connection_arn" {
  description = "GitHub connection to authorize in the AWS console"
  value       = module.demo_pipeline.github_connection_arn
}
