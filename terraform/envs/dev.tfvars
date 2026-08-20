# TANTU — dev environment
# Cost-optimized: Spot, ZONAL DB, small tiers, non-prod cleanup
project_id = "tantu-dev-XXXX" # <- replace with your dev project ID
region     = "asia-south1"
env        = "dev"

# Network
vpc_cidr = "10.10.0.0/16"

# GKE — Spot enabled for cost
gke_release_channel = "REGULAR"
enable_spot_nodes   = true

# Cloud SQL — cost-optimized, no HA in dev
postgres_version           = "POSTGRES_16"
postgres_tier              = "db-custom-1-3840"
postgres_disk_size_gb      = 20
postgres_ha_enabled        = false
postgres_deletion_protection = false

# Redis — BASIC in dev to save cost (override to STANDARD_HA if you test failover)
redis_memory_size_gb = 1
redis_version        = "REDIS_7_0"
redis_tier           = "BASIC"

# No GitHub trigger in dev by default (set to enable)
github_owner       = ""
github_repo        = ""
github_branch_regex = "^main$"

# State bucket — set after bootstrap: gsutil mb -l asia-south1 gs://tantu-dev-XXXX-tfstate
tf_state_bucket     = ""
create_state_bucket = false

# CUDs — not purchased via TF
enable_committed_use_discounts = false
