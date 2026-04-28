data "google_service_account" "default" {
  account_id = var.service_account_id
  project    = var.project_id
}

data "google_artifact_registry_repository" "my_repo" {
  project       = var.project_id
  location      = var.region
  repository_id = var.repo_name
}


data "google_project" "project" {
  project_id = var.project_id
}


resource "google_cloud_run_v2_service" "default" {
  name        = var.service_name
  location    = var.region
  project     = var.project_id
  ingress     = "INGRESS_TRAFFIC_ALL"
  iap_enabled = true

  template {
    service_account = data.google_service_account.default.email
    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/${data.google_artifact_registry_repository.my_repo.repository_id}/${var.image_name}:${var.image_tag}"
      ports {
        container_port = 8080
      }
      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }

      env {
        name  = "HOST"
        value = "/cloudsql/${google_sql_database_instance.instance.connection_name}"
      }

      env {
        name = "DATABASE_NAME"
        value_source {
          secret_key_ref {
            secret  = "AIW__DB_NAME"
            version = "latest"
          }
        }
      }

      env {
        name = "USER_NAME"
        value_source {
          secret_key_ref {
            secret  = "AIW__DB_USER_NAME"
            version = "latest"
          }
        }
      }

      env {
        name = "USER_PASSWORD"
        value_source {
          secret_key_ref {
            secret  = "AIW__DB_USER_PASSWORD"
            version = "latest"
          }
        }
      }

      env {
        name = "SECRET_KEY"
        value_source {
          secret_key_ref {
            secret  = "AIW__SECRET_KEY"
            version = "latest"
          }
        }
      }

      env {
        name = "USERNAME"
        value_source {
          secret_key_ref {
            secret  = "AIW__WEB_USERNAME"
            version = "latest"
          }
        }
      }

      env {
        name = "HASHED_PASSWORD"
        value_source {
          secret_key_ref {
            secret  = "AIW__HASHED_PASSWORD"
            version = "latest"
          }
        }
      }

      volume_mounts {
        name       = "cloudsql"
        mount_path = "/cloudsql"
      }

    }

    volumes {
      name = "cloudsql"
      cloud_sql_instance {

        instances = ["${google_sql_database_instance.instance.connection_name}"]
      }
    }

  }

}

resource "google_cloud_run_v2_service_iam_member" "iap_invoker" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.default.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-iap.iam.gserviceaccount.com"
}

resource "google_iap_web_cloud_run_service_iam_member" "iap_me" {
  project                = var.project_id
  location               = var.region
  cloud_run_service_name = google_cloud_run_v2_service.default.name
  role                   = "roles/iap.httpsResourceAccessor"
  member                 = "user:${var.iap_user_email}"
}
