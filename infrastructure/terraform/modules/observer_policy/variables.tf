variable "region" {
  type = string
}

variable "account_id" {
  type = string
}

variable "model_id" {
  type = string
}

variable "log_group_prefix" {
  type    = string
  default = "/ecs/aegisops/"
}
