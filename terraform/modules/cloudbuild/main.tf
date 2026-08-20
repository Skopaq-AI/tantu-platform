# Cloud Build — GitHub trigger -> Artifact Registry
# Requires Cloud Build GitHub App connected (https://console.cloud.google.com/cloud-build/triggers)

resource "google_cloudbuild_trigger" "github" {
  count       = var.create_trigger ? 1 : 0
  project     = var.project_id
  name        = "tantu-${var.env}-build"
  description = "TANTU ${var.env}: build images on push to ${var.branch_regex} -> ${var.artifact_repo_url}"

  github {
    owner = var.github_owner
    name  = var.github_repo
    push {
      branch = var.branch_regex
    }
  }

  filename = "cloudbuild.yaml"

  service_account = "projects/${var.project_id}/serviceAccounts/${var.project_id}@cloudbuild.gserviceaccount.com"

  include_build_logs = "INCLUDE_BUILD_LOGS_WITH_STATUS"

  tags = [var.env, "tantu"]
}

resource "google_storage_bucket" "cloudbuild_logs" {
  count                       = var.create_trigger ? 1 : 0
  name                        = "${var.project_id}-cloudbuild-logs-${var.env}"
  project                     = var.project_id
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age = 30
    }
  }

  labels = {
    env = var.env
  }
}
