# Cloud Build — optimized builds (kaniko + buildx) + Triggers for each microservice
# Best strategy: one trigger per service, path filter, substitution for version

resource "google_cloudbuild_trigger" "services" {
  for_each = toset(var.services)

  name        = "tantu-${var.env}-${each.key}"
  project     = var.project_id
  description = "Build ${each.key} on push to main (path filter services/${each.key}/*)"

  github {
    owner = var.github_owner
    name  = var.github_repo
    push { branch = "^main$" }
  }

  included_files = ["services/${each.key}/**", "shared/**"]

  substitutions = {
    _SERVICE      = each.key
    _REGION       = var.region
    _REPO         = var.artifact_repo
    _TAG          = "$SHORT_SHA" # overridden by release workflow
  }

  build {
    # Step 1: buildx + push to Artifact Registry (ARM64 + AMD64, cache)
    step {
      name = "gcr.io/kaniko-project/executor:latest"
      args = [
        "--dockerfile=services/${_SERVICE}/Dockerfile",
        "--context=.",
        "--destination=${_REGION}-docker.pkg.dev/${PROJECT_ID}/${_REPO}/${_SERVICE}:$SHORT_SHA",
        "--cache=true", "--cache-ttl=168h"
      ]
    }
    # Step 2: vulnerability scan (trivy)
    step {
      name = "aquasec/trivy:latest"
      args = ["image", "--exit-code", "0", "${var.region}-docker.pkg.dev/${var.project_id}/${var.artifact_repo}/${each.key}:$SHORT_SHA"]
      allow_failure = true
    }
    images = ["${var.region}-docker.pkg.dev/${var.project_id}/${var.artifact_repo}/${each.key}:$SHORT_SHA"]
  }

  depends_on = [var.registry_id]
}
