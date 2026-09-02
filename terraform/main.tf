provider "google" {
  project = var.project_id
  region  = var.region
}

data "google_artifact_registry_repository" "my_repo" {
  project       = var.project_id
  location      = var.region
  repository_id = var.repo_name
}


data "google_project" "project" {
  project_id = var.project_id
}
