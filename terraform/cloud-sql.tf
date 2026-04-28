resource "google_sql_database_instance" "instance" {
  name = "accounting-postgresql"

  region           = var.region
  project          = var.project_id
  database_version = "POSTGRES_18"

  settings {
    tier                        = "db-f1-micro"
    deletion_protection_enabled = true

    disk_type       = "PD_HDD"
    disk_size       = 10
    disk_autoresize = false

    ip_configuration {
      enable_private_path_for_google_cloud_services = true
      private_network                               = "projects/${var.project_id}/global/networks/default"
      authorized_networks {
        name  = "Looker-1"
        value = "142.251.74.0/23"
      }
      authorized_networks {
        name  = "Looker-2"
        value = "74.125.0.0/16"
      }

    }

    backup_configuration {
      binary_log_enabled             = false
      enabled                        = true
      location                       = "eu"
      point_in_time_recovery_enabled = true
      start_time                     = "03:00"
      transaction_log_retention_days = 7

      backup_retention_settings {
        retained_backups = 7
        retention_unit   = "COUNT"
      }
    }
  }
}
