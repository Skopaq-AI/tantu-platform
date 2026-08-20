# VPC + Subnet + Private Service Networking + NAT + Firewall

locals {
  subnet_cidr = var.subnet_cidr != null ? var.subnet_cidr : cidrsubnet(var.cidr, 4, 0) # /16 -> /20
}

resource "google_compute_network" "vpc" {
  name                    = var.vpc_name
  project                 = var.project_id
  auto_create_subnetworks = false
  routing_mode            = "REGIONAL"
  description             = "TANTU ${var.env} VPC — private service networking for Cloud SQL/Redis"
}

resource "google_compute_subnetwork" "primary" {
  name          = "${var.vpc_name}-subnet"
  project       = var.project_id
  region        = var.region
  network       = google_compute_network.vpc.id
  ip_cidr_range = local.subnet_cidr

  dynamic "secondary_ip_range" {
    for_each = var.secondary_ranges
    content {
      range_name    = secondary_ip_range.key
      ip_cidr_range = secondary_ip_range.value
    }
  }

  # Private Google Access required for private nodes to reach Google APIs
  private_ip_google_access = true

  log_config {
    aggregation_interval = "INTERVAL_10_MIN"
    flow_sampling        = 0.5
    metadata             = "INCLUDE_ALL_METADATA"
  }
}

# Cloud Router + NAT — private nodes need egress for image pull, OS patch, etc.
resource "google_compute_router" "router" {
  name    = "${var.vpc_name}-router"
  project = var.project_id
  region  = var.region
  network = google_compute_network.vpc.id
}

resource "google_compute_router_nat" "nat" {
  name                               = "${var.vpc_name}-nat"
  project                            = var.project_id
  region                             = var.region
  router                             = google_compute_router.router.name
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"

  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }
}

# Private Service Networking — global internal range + peering
resource "google_compute_global_address" "private_service" {
  count         = var.enable_private_service_networking ? 1 : 0
  name          = "${var.vpc_name}-psa-range"
  project       = var.project_id
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  address       = split("/", var.private_service_cidr)[0]
  network       = google_compute_network.vpc.id
}

resource "google_service_networking_connection" "private_vpc_connection" {
  count                   = var.enable_private_service_networking ? 1 : 0
  network                 = google_compute_network.vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_service[0].name]

  deletion_policy = "ABANDON"
}

# Minimal firewall — deny all ingress by default is GCP default; we add explicit allows
resource "google_compute_firewall" "allow_internal" {
  name    = "${var.vpc_name}-allow-internal"
  project = var.project_id
  network = google_compute_network.vpc.name

  direction = "INGRESS"
  priority  = 1000

  allow {
    protocol = "all"
  }
  source_ranges = [var.cidr]

  description = "Allow internal VPC communication (GKE <-> Cloud SQL / Redis via private IP)"
}

resource "google_compute_firewall" "allow_health_checks" {
  name    = "${var.vpc_name}-allow-health-checks"
  project = var.project_id
  network = google_compute_network.vpc.name

  direction = "INGRESS"
  priority  = 1000

  allow {
    protocol = "tcp"
  }
  # GCP health check ranges — required for GKE/Gateway
  source_ranges = ["130.211.0.0/22", "35.191.0.0/16"]

  target_tags = ["gke-node"]

  description = "Allow GCP health checks to GKE nodes"
}
