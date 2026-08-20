# TANTU — prod environment
# Production-grade: HA everywhere, no Spot, larger tiers, deletion protection, restricted ingress
project_id = "tantu-prod-XXXX" # <- replace with your prod project ID
region     = "asia-south1"
env        = "prod"

# Network
vpc_cidr = "10.20.0.0/16"

# GKE — prod uses on-demand (reliability), REGULAR channel with maintenance window
gke_release_channel = "REGULAR"
enable_spot_nodes   = false

# Cloud SQL — HA regional, larger tier, deletion protection ON
postgres_version              = "POSTGRES_16"
postgres_tier                 = "db-custom-2-7680" # 2 vCPU, 7.5GB — scale via console/TF
postgres_disk_size_gb         = 100
postgres_ha_enabled           = true
postgres_deletion_protection  = true

# Redis — HA
redis_memory_size_gb = 5
redis_version        = "REDIS_7_0"
redis_tier           = "STANDARD_HA"

# GitHub trigger — enable for prod CI
github_owner        = "your-org"
github_repo         = "tantu-platform"
github_branch_regex = "^main$"

# Security — restrict Gateway ingress to corp / WAF / Cloud Armor in prod
# Replace with your corp CIDRs + Cloud Armor policy attachment
allowed_ingress_cidrs = ["0.0.0.0/0"] # TODO: restrict to corp egress / WAF IP

# State bucket
tf_state_bucket     = ""
create_state_bucket = false

# CUDs — purchase 1y/3y committed use discounts out-of-band for prod base load
# See: gcloud compute commitments create / console Billing > Commitments
enable_committed_use_discounts = true
