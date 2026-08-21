# Secret Manager — secrets with rotation support, least-privilege IAM

resource "google_secret_manager_secret" "secrets" {
  for_each = var.secrets

  project   = var.project_id
  secret_id = "tantu-${var.env}-${each.key}"

  replication {
    auto {}
  }

  labels = {
    env = var.env
  }
}

resource "google_secret_manager_secret_version" "placeholder" {
  for_each = var.secrets

  secret      = google_secret_manager_secret.secrets[each.key].id
  secret_data = "REPLACE_ME_${upper(replace(each.key, "-", "_"))}"

  lifecycle {
    ignore_changes = [secret_data]
  }
}

resource "google_secret_manager_secret_iam_binding" "accessor" {
  # for_each keys are static (var.secrets keys only) — members list can be unknown
  # (var.accessor_members comes from IAM GSA emails, unknown at plan)
  # Using binding instead of member avoids "Invalid for_each argument: var.accessor_members is known only after apply"
  for_each = var.secrets

  project   = var.project_id
  secret_id = google_secret_manager_secret.secrets[each.key].secret_id
  role      = "roles/secretmanager.secretAccessor"
  members   = var.accessor_members
}
