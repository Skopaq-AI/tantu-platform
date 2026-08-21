# IAM — Workload Identity least privilege (GKE KSA → GCP SA)

resource "google_service_account" "tantu" {
  for_each     = var.workload_identity_bindings
  account_id   = "tantu-${var.env}-${replace(each.key, "/", "-")}"
  project      = var.project_id
  display_name = "TANTU ${var.env} ${each.key}"
}

resource "google_project_iam_member" "bindings" {
  for_each = { for pair in flatten([for k, v in var.workload_identity_bindings : [for r in v.roles : { k = k, role = r }]]) : "${pair.k}:${pair.role}" => pair }
  project  = var.project_id
  role     = each.value.role
  member   = "serviceAccount:${google_service_account.tantu[each.value.k].email}"
}

# Workload Identity binding (GSA → KSA) — DISABLED for bootstrap
# This requires GKE cluster's pool PROJECT_ID.svc.id.goog to exist (auto-created with GKE workload_identity_config).
# On first apply, GKE not yet created → fails 400 Identity Pool does not exist. So we skip it on initial apply
# and will be added back after GKE is READY (second apply). See main.tf comment.
# resource "google_service_account_iam_member" "wi" {
#   for_each           = var.workload_identity_bindings
#   service_account_id = google_service_account.tantu[each.key].name
#   role               = "roles/iam.workloadIdentityUser"
#   member             = "serviceAccount:${var.project_id}.svc.id.goog[${each.key}]"
# }
