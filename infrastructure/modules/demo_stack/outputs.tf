output "alb_dns_name" {
  description = "DNS name of the demo application load balancer"
  value       = aws_lb.main.dns_name
}

output "cloudfront_domain_name" {
  description = "CloudFront hostname available before the custom DNS cutover"
  value       = aws_cloudfront_distribution.demo.domain_name
}

output "cloudfront_distribution_id" {
  description = "ID of the demo CloudFront distribution"
  value       = aws_cloudfront_distribution.demo.id
}

output "ecs_cluster_name" {
  description = "Name of the demo ECS cluster"
  value       = aws_ecs_cluster.main.name
}

output "ecs_service_name" {
  description = "Name of the demo Hubble ECS service"
  value       = aws_ecs_service.hubble.name
}

output "site_url" {
  description = "URL for the demo, using the custom hostname when configured"
  value       = var.site_domain_name == "" ? "https://${aws_cloudfront_distribution.demo.domain_name}" : "https://${var.site_domain_name}"
}

output "target_group_arn" {
  description = "ARN of the demo Hubble target group"
  value       = aws_lb_target_group.hubble.arn
}

output "vpc_id" {
  description = "ID of the isolated demo VPC"
  value       = aws_vpc.main.id
}
