# Qdrant on GKE Autopilot — Helm release
# Autopilot-compatible: no hostPath, no privileged, uses PVC with standard-rwo
# For prod, scale to 3 replicas with anti-affinity and snapshot to GCS

# Providers are configured by root via google_client_config; this module assumes
# kubernetes/helm providers already authenticate to the cluster.

resource "kubernetes_namespace" "tantu" {
  metadata {
    name = var.namespace
    labels = {
      "name" = var.namespace
      "env"  = var.env
    }
  }
}

resource "helm_release" "qdrant" {
  name       = "qdrant"
  repository = "https://qdrant.github.io/qdrant-helm"
  chart      = "qdrant"
  version    = var.chart_version
  namespace  = kubernetes_namespace.tantu.metadata[0].name

  # Production values mirror infra/k8s/values*.yaml but Terraform is source of truth for infra Qdrant
  values = [
    yamlencode({
      replicaCount = var.env == "prod" ? 3 : var.replicas

      # Autopilot tuning — requests == limits recommended
      resources = {
        requests = { cpu = "500m", memory = "1Gi" }
        limits   = { cpu = "1000m", memory = "2Gi" }
      }

      # Autopilot Spot class for non-prod
      nodeSelector = var.enable_spot && var.env != "prod" ? {
        "cloud.google.com/compute-class" = "Scale-Out"
      } : {}

      # Persistence — use GKE standard storage class (CSI)
      persistence = {
        enabled      = true
        size         = var.env == "prod" ? "50Gi" : "10Gi"
        storageClass = "standard-rwo"
      }

      # Service — ClusterIP, Gateway routes to it
      service = {
        type = "ClusterIP"
        port = 6333
      }

      # Security — Autopilot requires runAsNonRoot, readOnlyRootFilesystem
      securityContext = {
        runAsNonRoot = true
        runAsUser    = 1000
        fsGroup      = 1000
      }

      # Liveness/Readiness — HTTP checks
      livenessProbe = {
        httpGet = { path = "/", port = 6333 }
        initialDelaySeconds = 30
      }
      readinessProbe = {
        httpGet = { path = "/readyz", port = 6333 }
        initialDelaySeconds = 10
      }

      # API key via Secret Manager — mounted via envFrom (created below)
      extraEnvVars = [
        { name = "QDRANT__SERVICE__API_KEY", valueFrom = { secretKeyRef = { name = "qdrant-api-key", key = "api-key" } } }
      ]
    })
  ]

  # Wait for rollout
  timeout = 600
  wait    = true

  depends_on = [kubernetes_namespace.tantu]
}

# API key secret — placeholder, rotate via Secret Manager and sync with external-secrets or manual kubectl
resource "random_password" "qdrant_api_key" {
  length  = 32
  special = false
}

resource "kubernetes_secret" "qdrant_api_key" {
  metadata {
    name      = "qdrant-api-key"
    namespace = kubernetes_namespace.tantu.metadata[0].name
  }
  data = {
    "api-key" = random_password.qdrant_api_key.result
  }
  type = "Opaque"
}

# Also sync to Secret Manager for non-k8s consumers
resource "google_secret_manager_secret" "qdrant_api_key" {
  secret_id = "tantu-${var.env}-qdrant-api-key"
  project   = var.project_id
  replication { auto {} }
  labels = { env = var.env }
}

resource "google_secret_manager_secret_version" "qdrant_api_key_version" {
  secret      = google_secret_manager_secret.qdrant_api_key.id
  secret_data = random_password.qdrant_api_key.result
}
