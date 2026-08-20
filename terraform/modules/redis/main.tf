# Memorystore for Redis — private IP, HA, transit encryption + AUTH

resource "google_redis_instance" "redis" {
  name           = "tantu-${var.env}-redis"
  project        = var.project_id
  region         = var.region
  tier           = var.tier
  memory_size_gb = var.memory_size_gb
  redis_version  = var.redis_version

  authorized_network = var.vpc_id
  connect_mode       = "PRIVATE_SERVICE_ACCESS"

  # Security hardening
  auth_enabled            = true
  transit_encryption_mode = "SERVER_AUTHENTICATION"

  maintenance_policy {
    weekly_maintenance_window {
      day = "SUNDAY"
      start_time { hours = 3 }
    }
  }

  redis_configs = {
    maxmemory-policy = "allkeys-lru"
    activedefrag     = "yes"
  }

  labels = { env = var.env }

  # For prod with cross-zone HA, Memorystore handles zone distribution internally
}

# Auth string stored in Secret Manager for app workloads
resource "google_secret_manager_secret" "redis_auth" {
  secret_id = "tantu-${var.env}-redis-auth"
  project   = var.project_id
  replication {
    auto {}
  }
  labels = {
    env = var.env
  }
}

resource "google_secret_manager_secret_version" "redis_auth_version" {
  secret      = google_secret_manager_secret.redis_auth.id
  secret_data = google_redis_instance.redis.auth_string
}
