variable "project_id" { type = string }
variable "region" { type = string }
variable "env" { type = string }
variable "vpc_id" { type = string }
variable "network" { type = string }
variable "memory_size_gb" { type = number }
variable "redis_version" { type = string }
variable "tier" { type = string }
variable "private_service_range" {
  type    = string
  default = null
}
