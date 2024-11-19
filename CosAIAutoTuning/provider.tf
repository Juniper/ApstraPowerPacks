terraform {
  required_providers {
    apstra = {
      source = "Juniper/apstra"
    }
  }
}

provider "apstra" {
  tls_validation_disabled = false
  blueprint_mutex_enabled = false
  experimental = true
}
