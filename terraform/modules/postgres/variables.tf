variable "project_id" { type = string }
variable "region" { type = string }
variable "env" { type = string }
variable "vpc_id" { type = string }
variable "vpc_self_link" { type = string }
variable "private_network" { type = string }
variable "postgres_version" { type = string }
variable "tier" { type = string }
variable "disk_size_gb" { type = number }
variable "ha_enabled" { type = bool }
variable "deletion_protection" { type = bool }
variable "private_ip_range" {
  type        = string
  description = "Private service range name"
  default     = null
}
variable "db_name" {
  type    = string
  default = "tantu"
}
variable "db_user" {
  type    = string
  default = "tantu_app"
}
