# TANTU Platform — Providers + Backend config + Project services
# Region default: asia-south1 (Mumbai) for data residency (DPDP 2023)

locals {
  # Centralised labels — cost allocation + governance
  common_labels = {
    project     = "tantu"
    env         = var.env
    managed_by  = "terraform"
    region      = var.region
    cost_center = "platform"
  }
  # GCS state bucket convention — override via var.tf_state_bucket if needed
  tf_state_bucket = var.tf_state_bucket != "" ? var.tf_state_bucket : "${var.project_id}-tfstate"
}

provider "google" {
  project = var.project_id
  region  = var.region
  # zone left unset — resources pin via var.zones / Autopilot
  default_labels = local.common_labels
}

provider "google-beta" {
  project        = var.project_id
  region         = var.region
  default_labels = local.common_labels
}

# Kubernetes + Helm providers authenticate via GKE cluster after creation.
# They use exec-free token via google_client_config data source to avoid
# storing kubeconfigs in state. Two-phase apply: first `terraform apply -target=module.gke -target=module.vpc`
# then full apply once cluster exists. Helm/K8s providers will error on first init before cluster — that is expected;
# use `terraform plan -target=module.gke` for bootstrap or set -var="enable_qdrant=false" if desired.
data "google_client_config" "default" {}

# GKE cluster data source — used to configure kubernetes/helm providers after cluster exists
# On first apply before cluster exists, these will fail gracefully; bootstrap without qdrant first.
data "google_container_cluster" "tantu" {
  count      = var.enable_qdrant_helm ? 1 : 0
  name       = "tantu-${var.env}-gke"
  location   = var.region
  project    = var.project_id
  depends_on = [google_project_service.required]
}

provider "kubernetes" {
  # During bootstrap (cluster not yet created), fallback to dummy values so `terraform init` succeeds
  host                   = try("https://${data.google_container_cluster.tantu[0].endpoint}", "https://127.0.0.1")
  token                  = data.google_client_config.default.access_token
  cluster_ca_certificate = try(base64decode(data.google_container_cluster.tantu[0].master_auth[0].cluster_ca_certificate), "")
}

provider "helm" {
  kubernetes {
    host                   = try("https://${data.google_container_cluster.tantu[0].endpoint}", "https://127.0.0.1")
    token                  = data.google_client_config.default.access_token
    cluster_ca_certificate = try(base64decode(data.google_container_cluster.tantu[0].master_auth[0].cluster_ca_certificate), "")
  }
}

# Enable required APIs — single place, explicit dependencies for all modules.
resource "google_project_service" "required" {
  for_each = toset([
    "compute.googleapis.com",
    "container.googleapis.com",
    "servicenetworking.googleapis.com",
    "sqladmin.googleapis.com",
    "redis.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "secretmanager.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "serviceusage.googleapis.com",
    "monitoring.googleapis.com",
    "logging.googleapis.com",
  ])
  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

# Optional: manage GCS state bucket itself (bootstrap mode).
# Set var.create_state_bucket = true ONLY on first apply with -target, then disable backend import.
# In normal flow, bucket is created out-of-band (make bootstrap-state) and this resource is not used.
resource "google_storage_bucket" "tfstate" {
  count    = var.create_state_bucket ? 1 : 0
  name     = local.tf_state_bucket
  location = var.region
  project  = var.project_id

  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false

  versioning { enabled = true }

  lifecycle_rule {
    action { type = "Delete" }
    condition {
      age        = 90
      with_state = "ARCHIVED"
    }
  }

  encryption {
    # Use Google-managed key by default; set var.kms_key_id for CMEK
    default_kms_key_name = var.kms_key_id
  }

  labels = local.common_labels
}
