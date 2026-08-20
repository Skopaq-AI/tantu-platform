variable "project_id" { type = string }
variable "region" { type = string }
variable "env" { type = string }
variable "format" {
  type    = string
  default = "DOCKER"
}
variable "repository_id" {
  type    = string
  default = "tantu"
}
