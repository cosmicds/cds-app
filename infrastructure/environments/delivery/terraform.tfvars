aws_region    = "us-east-1"
environment   = "production"
github_branch = "main"

github_repository            = "nmearl/cds-app"
codebuild_log_retention_days = 7

staging_portal_url          = "https://staging.app.cosmicds.cfa.harvard.edu"
staging_cluster_name        = "staging-cluster"
staging_portal_service_name = "staging-cds-portal"
staging_hubble_service_name = "staging-cds-hubble"

production_cluster_name        = "production-cluster"
production_portal_service_name = "production-cds-portal"
production_hubble_service_name = "production-cds-hubble"

# approval_notification_arn = "arn:aws:sns:us-east-1:072415053150:pipeline-approvals"
