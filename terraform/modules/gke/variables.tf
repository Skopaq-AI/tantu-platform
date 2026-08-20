variable "project_id" { type = string }
variable "region" { type = string }
variable "env" { type = string }
variable "cluster_name" { type = string }
variable "network" { type = string }
variable "subnetwork" { type = string }
variable "master_ipv4_cidr" {
  type        = string
  default     = "172.16.0.0/28"
}
variable "release_channel" {
  type        = string
  default     = "REGULAR"
}
variable "enable_spot" {
  type        = bool
  default     = true
  description = "Enable Autopilot Spot class for non-prod workloads (cost optimization)"
}
variable "gateway_class" {
  type        = string
  default     = "gke-l7-global-external-managed"
}
variable "deletion_protection" {
  type        = bool
  default     = true
}
