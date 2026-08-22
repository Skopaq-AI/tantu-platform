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

# Random placeholder — generated securely; rotate via gcloud secrets versions add
# Value is usable immediately and is ignored on updates (lifecycle ignore_changes)
resource "random_password" "placeholder" {
  for_each = var.secrets
  length  = 32
  special = true
  # Keep Terraform formatting stable: allow common specials that are shell-safe
  override_special = "_-"
}

resource "google_secret_manager_secret_version" "placeholder" {
  for_each = var.secrets

  secret      = google_secret_manager_secret.secrets[each.key].id
  secret_data = random_password.placeholder[each.key].result

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
