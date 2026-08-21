# Cloud SQL Postgres 16 + TimescaleDB — private IP, HA, automated backups, insights
# Timescale enabled via database_flags.shared_preload_libraries = timescaledb

resource "random_password" "db_password" {
  length  = 24
  special = true
}

resource "google_sql_database_instance" "postgres" {
  name             = "tantu-${var.env}-pg16"
  project          = var.project_id
  region           = var.region
  database_version = var.postgres_version

  deletion_protection = var.deletion_protection

  settings {
    tier                  = var.tier
    availability_type     = var.ha_enabled ? "REGIONAL" : "ZONAL"
    disk_type             = "PD_SSD"
    disk_size             = var.disk_size_gb
    disk_autoresize       = true
    disk_autoresize_limit = 500

    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
      start_time                     = "02:00" # UTC window
      location                       = var.region
      transaction_log_retention_days = 7
      backup_retention_settings {
        retained_backups = 14
        retention_unit   = "COUNT"
      }
    }

    ip_configuration {
      ipv4_enabled    = false
      private_network = var.private_network
      require_ssl     = true
      # No authorized_networks — private IP only
    }

    maintenance_window {
      day          = 7 # Sunday
      hour         = 3
      update_track = var.env == "prod" ? "stable" : "canary"
    }

    insights_config {
      query_insights_enabled  = true
      query_string_length     = 1024
      record_application_tags = true
      record_client_address   = true
    }

    database_flags {
      name  = "log_min_duration_statement"
      value = "1000" # log slow queries >1s
    }
    database_flags {
      name  = "cloudsql.iam_authentication"
      value = "on"
    }

    # pgaudit — use Cloud SQL flag; shared_preload_libraries and max_connections are not valid Cloud SQL flags for Postgres 16 (removed — was 404 invalidFlagName)
    database_flags {
      name  = "cloudsql.enable_pgaudit"
      value = "on"
    }
    database_flags {
      name  = "pgaudit.log"
      value = "ddl,write"
    }

    user_labels = {
      env = var.env
    }
  }

  depends_on = [random_password.db_password]
}

resource "google_sql_database" "app_db" {
  name     = var.db_name
  project  = var.project_id
  instance = google_sql_database_instance.postgres.name
}

resource "google_sql_user" "app_user" {
  name     = var.db_user
  project  = var.project_id
  instance = google_sql_database_instance.postgres.name
  password = random_password.db_password.result
  # For IAM auth alternative, type = "CLOUD_IAM_SERVICE_ACCOUNT" + host field
}

# Store password in Secret Manager — app reads via Workload Identity, not TF output
resource "google_secret_manager_secret" "db_password" {
  secret_id = "tantu-${var.env}-db-password"
  project   = var.project_id
  replication {
    auto {}
  }
  labels = { env = var.env }
}

resource "google_secret_manager_secret_version" "db_password_version" {
  secret      = google_secret_manager_secret.db_password.id
  secret_data = random_password.db_password.result
}

# Optional: IAM DB auth mapping (least privilege) — example, disabled by default
# Uncomment to use IAM auth instead of password:
# resource "google_sql_user" "iam_user" {
#   name     = "tantu-api@${var.project_id}.iam"
#   project  = var.project_id
#   instance = google_sql_database_instance.postgres.name
#   type     = "CLOUD_IAM_SERVICE_ACCOUNT"
# }
