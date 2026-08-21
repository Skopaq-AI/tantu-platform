# TANTU Platform — Root composition
# Best deployment strategy inline: Autopilot + Gateway API + Argo Rollouts canary
# See infra/k8s/values*.yaml and docs below

locals {
  name_prefix = "tantu-${var.env}"
  # Gateway class for GKE Gateway API (external L7)
  gateway_class = "gke-l7-global-external-managed"

  # Common resource naming
  network_name = "${local.name_prefix}-vpc"
  cluster_name = "${local.name_prefix}-gke"
}

# ──────────────────────────────────────────────
# VPC + Private Service Networking
# ──────────────────────────────────────────────
module "vpc" {
  source = "./modules/vpc"

  project_id                        = var.project_id
  region                            = var.region
  env                               = var.env
  vpc_name                          = local.network_name
  cidr                              = var.vpc_cidr
  enable_private_service_networking = var.enable_private_service_networking

  depends_on = [google_project_service.required]
}

# ──────────────────────────────────────────────
# Artifact Registry (must exist before GKE pulls)
# ──────────────────────────────────────────────
module "registry" {
  source = "./modules/registry"

  project_id = var.project_id
  region     = var.region
  env        = var.env
  format     = var.registry_format

  depends_on = [google_project_service.required]
}

# ──────────────────────────────────────────────
# Cloud SQL Postgres 16 + Timescale (private IP, HA in prod)
# ──────────────────────────────────────────────
module "postgres" {
  source = "./modules/postgres"

  project_id          = var.project_id
  region              = var.region
  env                 = var.env
  vpc_id              = module.vpc.vpc_id
  vpc_self_link       = module.vpc.vpc_self_link
  private_network     = module.vpc.vpc_self_link
  postgres_version    = var.postgres_version
  tier                = var.postgres_tier
  disk_size_gb        = var.postgres_disk_size_gb
  ha_enabled          = var.postgres_ha_enabled
  deletion_protection = var.postgres_deletion_protection
  private_ip_range    = module.vpc.private_service_range

  depends_on = [module.vpc]
}

# ──────────────────────────────────────────────
# Memorystore Redis (private service networking)
# ──────────────────────────────────────────────
module "redis" {
  source = "./modules/redis"

  project_id            = var.project_id
  region                = var.region
  env                   = var.env
  vpc_id                = module.vpc.vpc_id
  network               = module.vpc.vpc_self_link
  memory_size_gb        = var.redis_memory_size_gb
  redis_version         = var.redis_version
  tier                  = var.redis_tier
  private_service_range = module.vpc.private_service_range

  depends_on = [module.vpc]
}

# ──────────────────────────────────────────────
# IAM + Workload Identity (least privilege)
# ──────────────────────────────────────────────
module "iam" {
  source = "./modules/iam"

  project_id         = var.project_id
  region             = var.region
  env                = var.env
  cluster_name       = local.cluster_name
  artifact_repo_name = module.registry.repository_name
  # Namespace/KSAs that will be bound — must match Helm release serviceAccounts
  workload_identity_bindings = {
    "tantu/api"    = { roles = ["roles/cloudsql.client", "roles/secretmanager.secretAccessor"] }
    "tantu/worker" = { roles = ["roles/cloudsql.client"] }
    "tantu/qdrant" = { roles = ["roles/storage.objectViewer"] }
  }

  depends_on = [module.registry]
}

# ──────────────────────────────────────────────
# GKE Autopilot + Gateway API + Workload Identity + Artifact Registry auth
# ──────────────────────────────────────────────
module "gke" {
  source = "./modules/gke"

  project_id       = var.project_id
  region           = var.region
  env              = var.env
  cluster_name     = local.cluster_name
  network          = module.vpc.vpc_self_link
  subnetwork       = module.vpc.subnet_self_link
  master_ipv4_cidr = var.gke_master_ipv4_cidr
  release_channel  = var.gke_release_channel
  enable_spot      = var.enable_spot_nodes
  gateway_class    = local.gateway_class

  depends_on = [module.vpc, module.iam, google_project_service.required]
}

# ──────────────────────────────────────────────
# Secret Manager (app secrets — not TF state)
# ──────────────────────────────────────────────
module "secrets" {
  source = "./modules/secrets"

  project_id = var.project_id
  region     = var.region
  env        = var.env
  # Secrets created with random values as placeholders — rotate via gcloud or console
  secrets = {
    "db-password"     = { replication = "automatic" }
    "jwt-private-key" = { replication = "automatic" }
    "qdrant-api-key"  = { replication = "automatic" }
    "gemini-api-key"  = { replication = "automatic" }
    "hf-token"        = { replication = "automatic" }
  }
  # Grant accessor to workload GSAs
  accessor_members = distinct(flatten([
    for _, sa in module.iam.workload_gsa_emails : ["serviceAccount:${sa}"]
  ]))

  depends_on = [google_project_service.required]
}

# ──────────────────────────────────────────────
# Cloud Build trigger (CI -> Artifact Registry)
# ──────────────────────────────────────────────
module "cloudbuild" {
  source = "./modules/cloudbuild"

  project_id        = var.project_id
  region            = var.region
  env               = var.env
  github_owner      = var.github_owner
  github_repo       = var.github_repo
  branch_regex      = var.github_branch_regex
  artifact_repo_url = module.registry.repository_url

  # Skip creation if GitHub not configured
  create_trigger = var.github_owner != "" && var.github_repo != ""

  depends_on = [module.registry, google_project_service.required]
}

# ──────────────────────────────────────────────
# Qdrant on GKE (Helm release via kubernetes/helm providers)
# Deployed AFTER GKE is ready — uses Helm provider with GKE auth
# Two-phase: first apply with -var="enable_qdrant_helm=false", then true once cluster exists
# ──────────────────────────────────────────────
module "qdrant" {
  count  = var.enable_qdrant_helm ? 1 : 0
  source = "./modules/qdrant"

  project_id             = var.project_id
  env                    = var.env
  cluster_name           = module.gke.cluster_name
  cluster_endpoint       = module.gke.cluster_endpoint
  cluster_ca_certificate = module.gke.cluster_ca_certificate
  namespace              = "tantu"
  enable_spot            = var.enable_spot_nodes

  depends_on = [module.gke, module.iam]
}

# ──────────────────────────────────────────────
# Helm provider auth — deferred: configured via provider aliases above
# For terraform apply, ensure gcloud auth and GKE IAM; for CI use Workload Identity Federation
# ──────────────────────────────────────────────


# ──────────────────────────────────────────────
# GitHub Actions Deployer SA + WIF (for CD + Infra workflows)
# Creates: tantu-gha-deployer SA + github WIF pool/provider + principalSet binding
# Use outputs to set GitHub Secrets/Vars: GCP_WIP, GCP_SA
# ──────────────────────────────────────────────
module "github_deployer" {
  source         = "./modules/github-deployer"
  project_id     = var.project_id
  project_number = data.google_project.current.number
  github_owner   = var.github_owner != "" ? var.github_owner : "Skopaq-AI"
  github_repo    = var.github_repo != "" ? var.github_repo : "tantu-platform"
  pool_id        = "github"
  provider_id    = "github-provider"
  sa_id          = "tantu-gha-deployer"
  # TF state bucket is created by gcp-beta-apply.sh; set true here if you want TF to manage it
  create_state_bucket = var.create_state_bucket

  depends_on = [google_project_service.required]
}

data "google_project" "current" {
  project_id = var.project_id
}

# Argo Rollouts controller — installed via Helm in GKE module (see modules/gke)
# Gateway + HTTPRoute + Rollout manifests live in infra/k8s/ (values.yaml, gateway.yaml, rollout.yaml)
# Apply after Terraform: kubectl apply -f infra/k8s/ or via ArgoCD
