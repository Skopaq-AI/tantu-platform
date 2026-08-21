variable "project_id" {
  type = string
}
variable "project_number" {
  type = string
}
variable "github_owner" {
  type    = string
  default = "Skopaq-AI"
}
variable "github_repo" {
  type    = string
  default = "tantu-platform"
}
variable "pool_id" {
  type    = string
  default = "github"
}
variable "provider_id" {
  type    = string
  default = "github-provider"
}
variable "sa_id" {
  type    = string
  default = "tantu-gha-deployer"
}
variable "sa_display_name" {
  type    = string
  default = "TANTU GitHub Actions Deployer"
}
variable "create_state_bucket" {
  type    = bool
  default = false
}
variable "state_bucket_location" {
  type    = string
  default = "asia-south1"
}
