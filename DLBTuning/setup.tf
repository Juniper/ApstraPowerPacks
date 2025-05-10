terraform {
  required_providers {
    apstra = {
      source  = "Juniper/apstra"
    }
  }
}

provider "apstra" {
  #  url = "https://user:password@apstraurl" Fill this out or
  #  export APSTRA_URL, APSTRA_USER and APSTRA_PASS
  experimental            = true # Needed for any version > 4.2.1
  tls_validation_disabled = true
  blueprint_mutex_enabled = false
}

variable "blueprint_name" {
  type = string
}

variable "lb_policy" {
  type = string
}
variable "inactivity_timer_delta" {
  type = number
}


locals {
    payload = jsonencode({
      pause = false
      blueprint = var.blueprint_name
      lb_policy = var.lb_policy
      inactivity_timer_delta = var.inactivity_timer_delta
    })
  }
resource "apstra_property_set" "ps" {
  data = local.payload
  name = "DLB Manager"
}