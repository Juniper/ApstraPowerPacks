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

# This example outputs a list of blueprint IDs
data "apstra_blueprints" "d" {
  reference_design = "datacenter" // optional filter argument
}

  locals {
    payload = jsonencode({
      pause = false
      blueprint_ids = data.apstra_blueprints.d.ids
    })
  }
resource "apstra_property_set" "ps" {
  data = local.payload
  name = "Ticket Manager"
}