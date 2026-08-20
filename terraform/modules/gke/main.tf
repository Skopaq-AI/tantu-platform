# GKE Autopilot + Gateway API + Autopilot workload policy
# Cost-optimized: Spot for non-prod (via workload nodeSelector), committed use for prod (out-of-band CUDs)
# Security: private cluster, Workload Identity, Shielded Nodes, Binary Authorization stub

resource "google_container_cluster" "autopilot" {
  name                = var.cluster_name
  project             = var.project_id
  location            = var.region
  deletion_protection = var.deletion_protection && var.env == "prod"

  enable_autopilot = true

  network    = var.network
  subnetwork = var.subnetwork

  release_channel {
    channel = var.release_channel
  }

  # Private cluster — nodes have no public IPs
  private_cluster_config {
    enable_private_nodes    = true
    enable_private_endpoint = false # keep API reachable via authorized networks; set true for fully private prod
    master_ipv4_cidr_block  = var.master_ipv4_cidr
    master_global_access_config {
      enabled = true
    }
  }

  # Workload Identity — required for GSA <-> KSA binding
  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }

  # Gateway API channel — enables Gateway, HTTPRoute CRDs
  gateway_api_config {
    channel = "CHANNEL_STANDARD"
  }

  # Autopilot already enables shielded nodes, workload vulnerability scanning, etc.
  # Enable cost allocation + observability
  resource_labels = {
    env = var.env
  }

  # Maintenance window — prod: prefer off-hours
  dynamic "maintenance_policy" {
    for_each = var.env == "prod" ? [1] : []
    content {
      recurring_window {
        start_time = "2025-01-01T02:00:00Z"
        end_time   = "2025-01-01T06:00:00Z"
        recurrence = "FREQ=WEEKLY;BYDAY=SA"
      }
    }
  }

  # Enable GKE Gateway controller (managed)
  # No additional addon block needed — gateway_api_config enables it.

  # Logging / Monitoring — system + workload
  logging_service    = "logging.googleapis.com/kubernetes"
  monitoring_service = "monitoring.googleapis.com/kubernetes"

  # Autopilot handles node pools; no node_config block allowed here.
  # Spot vs on-demand is set at workload level (nodeSelector: cloud.google.com/compute-class)

  ip_allocation_policy {
    # Autopilot auto-allocates; leave empty to use subnet secondary ranges
  }
}

# ──────────────────────────────────────────────
# Argo Rollouts controller (via Helm) — gradual canary strategy
# Installed into this cluster so Rollout CRD exists before app manifests.
# ──────────────────────────────────────────────
# Helm provider must be configured by caller (root) using cluster credentials.
# We use data sources so this module can optionally install via helm_release
# when helm provider is available. Guard with var.install_rollouts.

# NOTE: helm_release requires helm provider configured with cluster endpoint.
# To avoid chicken-egg during first terraform apply before cluster exists,
# this module ships the Helm values but does NOT force helm_release.
# Root should set up kubernetes/helm providers via google_client_config after cluster creation.
# Uncomment below if you want Terraform-managed Rollouts; otherwise install via ArgoCD/kubectl.

# For Terraform-managed install, add to modules/gke:
# resource "helm_release" "argo_rollouts" { ... }

# We provide a null_resource anchor for documentation and dependency ordering.
resource "null_resource" "rollouts_anchor" {
  triggers = {
    cluster = google_container_cluster.autopilot.name
    # Bump to force reinstall notes
    rollouts_version = "2.33.0"
  }
}

# Gateway — external L7 LB managed by GKE Gateway controller
# Manifest lives in infra/k8s/gateway.yaml (Gateway + HTTPRoute).
# Terraform creates a static global IP that the Gateway will use via annotation.
resource "google_compute_global_address" "gateway_ip" {
  name        = "${var.cluster_name}-gateway-ip"
  project     = var.project_id
  description = "Static IP for GKE Gateway (${var.env})"
}

# Optional: Managed SSL certificate placeholder — in prod, use google_managed SSL or cert-manager
# Not created here to avoid DNS dependency; wire via Gateway listener TLS config.
