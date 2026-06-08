aws_region         = "us-east-1"
environment        = "production"
site_domain_name   = "app.cosmicds.cfa.harvard.edu"
certificate_domain = "app.cosmicds.cfa.harvard.edu"

cds_portal_image = "072415053150.dkr.ecr.us-east-1.amazonaws.com/cds-portal:latest"
cds_hubble_image = "072415053150.dkr.ecr.us-east-1.amazonaws.com/cds-hubble:latest"

cds_portal_min_capacity           = 1
cds_portal_max_capacity           = 3
cds_hubble_min_capacity           = 2
cds_hubble_max_capacity           = 4
enable_cluster_capacity_providers = false
enable_container_insights         = false
use_capacity_provider_strategy    = false
create_private_nat_gateways       = false
use_private_service_subnets       = false
log_group_class                   = "STANDARD"
app_log_retention_days            = 3

cds_portal_cpu    = 256
cds_portal_memory = 512
cds_hubble_cpu    = 1024
cds_hubble_memory = 2048
