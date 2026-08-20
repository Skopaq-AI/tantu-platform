# Artifact Registry — Docker, with lifecycle, cleanup, and IAM

resource "google_artifact_registry_repository" "tantu" {
  provider = google-beta

  project       = var.project_id
  location      = var.region
  repository_id = var.repository_id
  format        = var.format
  description   = "TANTU ${var.env} — backend, frontend, adapter images"

  docker_config {
    immutable_tags = var.env == "prod" # prevent tag overwrite in prod
  }

  cleanup_policies {
    id     = "keep-recent-20"
    action = "KEEP"
    most_recent_versions {
      keep_count = 20
    }
  }

  cleanup_policies {
    id     = "delete-untagged"
    action = "DELETE"
    condition {
      tag_state    = "UNTAGGED"
      older_than   = "2592000s" # 30d
    }
  }

  cleanup_policies {
    id     = "keep-prod-images"
    action = "KEEP"
    condition {
      tag_state  = "TAGGED"
      tag_prefixes = ["prod-", "v"]
    }
    most_recent_versions { keep_count = 50 }
  }

  labels = { env = var.env }
}

# Cleanup policy dry-run is implicit; use console to preview
