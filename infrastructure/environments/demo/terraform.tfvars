aws_region  = "us-east-1"
environment = "demo"

# Leave these empty while the current production CloudFront distribution owns
# app.cosmicds.cfa.harvard.edu. Set both values during the final DNS cutover.
site_domain_name   = ""
certificate_domain = ""

github_repository = "cosmicds/cds-app"
github_branch     = "main"

ecr_repository_name = "cds-hubble-demo"

enable_autoscaling = false
desired_count      = 1
min_capacity       = 1
max_capacity       = 2

hubble_cpu    = 512
hubble_memory = 1024

app_log_retention_days       = 3
codebuild_log_retention_days = 7
