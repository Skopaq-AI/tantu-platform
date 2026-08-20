# TANTU Platform — Input variables
# Best practices: typed, validated, documented, env-aware defaults.

variable "project_id" {
  description = "GCP project ID (must exist). Used for all resources and state bucket naming."
  type        = string
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{4,28}[a-z0-9]$", var.project_id))
    error_message = "project_id must be 6-30 chars, lowercase, hyphens, start with letter."
  }
}

variable "region" {
  description = "Primary GCP region — DPDP residency default asia-south1 (Mumbai)."
  type        = string
  default     = "asia-south1"
  validation {
    condition     = can(regex("^[a-z]+-[a-z]+[0-9]$", var.region))
    error_message = "region must be like asia-south1, us-central1, etc."
  }
}

variable "env" {
  description = "Environment name: dev | staging | prod"
  type        = string
  default     = "dev"
  validation {
    condition     = contains(["dev", "staging", "prod"], var.env)
    error_message = "env must be dev, staging, or prod."
  }
}

variable "zones" {
  description = "Zones for regional resources. Null = provider auto."
  type        = list(string)
  default     = null
}

# ── Network ──
variable "vpc_cidr" {
  description = "VPC primary CIDR"
  type        = string
  default     = "10.10.0.0/16"
}

variable "enable_private_service_networking" {
  description = "Create private service networking for Cloud SQL / Memorystore private IP"
  type        = bool
  default     = true
}

# ── GKE ──
variable "gke_release_channel" {
  description = "GKE release channel"
  type        = string
  default     = "REGULAR"
  validation {
    condition     = contains(["RAPID", "REGULAR", "STABLE"], var.gke_release_channel)
    error_message = "Must be RAPID, REGULAR, or STABLE."
  }
}

variable "enable_spot_nodes" {
  description = "Use Spot for non-prod cost optimization (Autopilot workload class). Overridden to false in prod tfvars."
  type        = bool
  default     = true
}

variable "gke_master_ipv4_cidr" {
  description = "Private cluster master CIDR /28"
  type        = string
  default     = "172.16.0.0/28"
}

# ── Cloud SQL ──
variable "postgres_version" {
  description = "Postgres major version — 16 + Timescale extension enabled via flags"
  type        = string
  default     = "POSTGRES_16"
}

variable "postgres_tier" {
  description = "Cloud SQL tier. Dev default db-custom-1-3840, prod via tfvars overrides to db-custom-2-7680+"
  type        = string
  default     = "db-custom-1-3840"
}

variable "postgres_disk_size_gb" {
  type        = number
  default     = 50
  description = "Initial disk size GB"
}

variable "postgres_ha_enabled" {
  description = "HA (regional) — true in prod, false in dev for cost"
  type        = bool
  default     = false
}

variable "postgres_deletion_protection" {
  type        = bool
  default     = true
  description = "Protect prod DB from accidental destroy"
}

# ── Redis ──
variable "redis_memory_size_gb" {
  type        = number
  default     = 1
  description = "Memorystore Redis memory GB"
}

variable "redis_version" {
  type    = string
  default = "REDIS_7_0"
}

variable "redis_tier" {
  type        = string
  default     = "STANDARD_HA"
  description = "BASIC or STANDARD_HA"
}

# ── Artifact Registry ──
variable "registry_format" {
  type    = string
  default = "DOCKER"
}

# ── State / Security ──
variable "tf_state_bucket" {
  description = "Override GCS state bucket name. Empty = <project_id>-tfstate"
  type        = string
  default     = ""
}

variable "create_state_bucket" {
  description = "Create state bucket via Terraform (bootstrap only). Normal flow: false — create via gcloud."
  type        = bool
  default     = false
}

variable "kms_key_id" {
  description = "CMEK key self-link for GCS bucket encryption. Empty = Google-managed."
  type        = string
  default     = null
}

variable "allowed_ingress_cidrs" {
  description = "CIDRs allowed to reach Gateway external LB (prod should restrict to corp/WAF)."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

# ── Cloud Build ──
variable "github_owner" {
  type        = string
  default     = ""
  description = "GitHub owner/org for Cloud Build trigger (empty = skip trigger)."
}

variable "github_repo" {
  type        = string
  default     = ""
  description = "GitHub repo name for Cloud Build trigger."
}

variable "github_branch_regex" {
  type    = string
  default = "^main$"
}

# ── Tags / Cost ──
variable "enable_committed_use_discounts" {
  description = "Flag for documentation/CUD purchase reminder — CUDs are purchased out-of-band, not via TF."
  type        = bool
  default     = false
}

variable "enable_qdrant_helm" {
  description = "Enable Helm-based Qdrant on GKE. Set false for bootstrap phase before cluster exists."
  type        = bool
  default     = true
}
