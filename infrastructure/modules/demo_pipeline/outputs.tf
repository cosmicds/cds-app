output "codepipeline_name" {
  description = "Name of the demo Hubble CodePipeline"
  value       = aws_codepipeline.demo.name
}

output "github_connection_arn" {
  description = "ARN of the GitHub connection that must be authorized after creation"
  value       = aws_codestarconnections_connection.github.arn
}
