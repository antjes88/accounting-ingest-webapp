terraform {
  required_version = ">= 1.0"
  backend "gcs" {
    bucket = "terraform-state-v8q0qvfi"
    prefix = "terraform/state/accounting-ingest-webapp"
  }

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 7.29.0"
    }
  }
}
