# TANTU Platform — Terraform version constraints
# Follows best practices: pinned providers, >= Terraform 1.5 for import blocks & checks

terraform {
  required_version = ">= 1.6.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.27"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.12"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # Remote state — GCS backend. Bucket must be bootstrapped before first init.
  # See README.md "Bootstrap remote state" or run: make bootstrap-state
  # Bucket naming: <project_id>-tfstate (see provider.tf locals)
  backend "gcs" {}
}

# Provider aliases are configured in provider.tf
