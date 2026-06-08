aws_region         = "us-east-1"
environment        = "staging"
site_domain_name   = "staging.app.cosmicds.cfa.harvard.edu"
certificate_domain = "*.app.cosmicds.cfa.harvard.edu"

cds_portal_image         = "072415053150.dkr.ecr.us-east-1.amazonaws.com/cds-portal:staging"
cds_hubble_image         = "072415053150.dkr.ecr.us-east-1.amazonaws.com/cds-hubble:staging"
portal_secret_source_arn = "arn:aws:secretsmanager:us-east-1:072415053150:secret:production/cds-portal/secrets-U1KCLt"
hubble_secret_source_arn = "arn:aws:secretsmanager:us-east-1:072415053150:secret:production/cds-hubble/secrets-SH3xIk"

cds_portal_min_capacity           = 1
cds_portal_max_capacity           = 2
cds_hubble_min_capacity           = 1
cds_hubble_max_capacity           = 2
enable_autoscaling                = false
enable_cluster_capacity_providers = false
enable_container_insights         = false
use_capacity_provider_strategy    = false
use_private_service_subnets       = false
create_private_nat_gateways       = false
log_group_class                   = "STANDARD"
app_log_retention_days            = 3
cloudfront_origin_protocol_policy = "http-only"

cds_portal_cpu    = 256
cds_portal_memory = 512
cds_hubble_cpu    = 512
cds_hubble_memory = 1024
