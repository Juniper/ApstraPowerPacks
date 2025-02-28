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
      ignore_anomalies=  [],      #List of Anomalies to Ignore
      ignore_devices= [],         #List of device hostnames to ignore
      include_only_anomalies= [], #List of anomalies to include, all others will be ignored
      include_only_devices= [],   #List of devices to include, all others will be ignored
      include_only_severity: [],  #List of severities to include, all others will be ignored
    })
  }
resource "apstra_property_set" "ps" {
  data = local.payload
  name = "Ticket Manager"
}