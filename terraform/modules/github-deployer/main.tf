# github-deployer — Service Account + Workload Identity Federation for GitHub Actions
# OIDC without JSON keys. Bind GitHub repo Skopaq-AI/tantu-platform -> GCP SA.

resource "google_service_account" "deployer" {
  account_id   = var.sa_id
  project      = var.project_id
  display_name = var.sa_display_name
  description  = "GitHub Actions — builds + pushes to Artifact Registry + GKE deploy + TF state"
}

resource "google_project_iam_member" "deployer_roles" {
  for_each = toset([
    "roles/artifactregistry.admin",
    "roles/artifactregistry.writer",
    "roles/container.admin",
    "roles/container.clusterAdmin",
    "roles/iam.serviceAccountAdmin",
    "roles/iam.serviceAccountUser",
    "roles/storage.admin",
    "roles/cloudsql.admin",
    "roles/secretmanager.admin",
    "roles/secretmanager.secretAccessor",
    "roles/secretmanager.viewer",
    "roles/compute.admin",
    "roles/compute.viewer",
    "roles/iam.workloadIdentityPoolAdmin",
    "roles/resourcemanager.projectIamAdmin",
    "roles/serviceusage.serviceUsageAdmin",
    "roles/servicenetworking.admin",
    "roles/redis.admin",
  ])
  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.deployer.email}"
}

resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = var.pool_id
  project                   = var.project_id
  display_name              = "GitHub"
  description               = "GitHub Actions OIDC"
  disabled                  = false
}

resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = var.provider_id
  project                            = var.project_id
  display_name                       = "GitHub OIDC"
  description                        = "GitHub Actions OIDC provider"

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
    "attribute.actor"      = "assertion.actor"
    "attribute.aud"        = "assertion.aud"
    "attribute.ref"        = "assertion.ref"
  }
  attribute_condition = "assertion.repository == \"${var.github_owner}/${var.github_repo}\""

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

resource "google_service_account_iam_member" "wif_binding" {
  service_account_id = google_service_account.deployer.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/projects/${var.project_number}/locations/global/workloadIdentityPools/${google_iam_workload_identity_pool.github.workload_identity_pool_id}/attribute.repository/${var.github_owner}/${var.github_repo}"
  depends_on         = [google_iam_workload_identity_pool_provider.github]
}

resource "google_service_account_iam_member" "sa_user_self" {
  service_account_id = google_service_account.deployer.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.deployer.email}"
}

resource "google_storage_bucket" "tfstate" {
  count                       = var.create_state_bucket ? 1 : 0
  name                        = "${var.project_id}-tfstate"
  location                    = var.state_bucket_location
  project                     = var.project_id
  uniform_bucket_level_access = true
  versioning { enabled = true }
  lifecycle { prevent_destroy = false }
}
