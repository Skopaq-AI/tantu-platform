variable "project_id" {
  type = string
}

variable "region" {
  type = string
}

variable "env" {
  type = string
}

variable "github_owner" {
  type = string
}

variable "github_repo" {
  type = string
}

variable "branch_regex" {
  type = string
}

variable "artifact_repo_url" {
  type = string
}

variable "create_trigger" {
  type    = bool
  default = false
}
