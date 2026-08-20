variable "project_id" { type = string }
variable "env" { type = string }
variable "cluster_name" { type = string }
variable "cluster_endpoint" { type = string }
variable "cluster_ca_certificate" { type = string }
variable "namespace" {
  type    = string
  default = "tantu"
}
variable "enable_spot" {
  type    = bool
  default = true
}
variable "chart_version" {
  type    = string
  default = "0.8.6"
}
variable "replicas" {
  type    = number
  default = 1
}
