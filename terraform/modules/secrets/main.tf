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

resource "google_secret_manager_secret_iam_member" "accessor" {
  for_each = {
    for pair in setproduct(keys(var.secrets), var.accessor_members) : "${pair[0]}__${pair[1]}" => {
      secret = pair[0]
      member = pair[1]
    }
  }

  project   = var.project_id
  secret_id = google_secret_manager_secret.secrets[each.value.secret].secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = each.value.member
}
