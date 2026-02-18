locals {
  base_name    = "a3-ai-news"
  project_id   = "a3-team-481403"
  region       = "australia-southeast1"
  service_name = local.base_name

  # GitHub repository (for Cloud Build trigger)
  github_owner = "bolongwang-boop"
  github_repo  = "a3-ai-news"

  # Database configuration
  db_name     = "ai_news"
  db_tier     = "db-f1-micro"
  db_version  = "POSTGRES_15"
  db_user     = "ainews"

  # Required GCP services
  project_services = [
    "run.googleapis.com",
    "cloudbuild.googleapis.com",
    "artifactregistry.googleapis.com",
    "secretmanager.googleapis.com",
    "iam.googleapis.com",
    "sqladmin.googleapis.com",
    "vpcaccess.googleapis.com",
    "servicenetworking.googleapis.com",
  ]
}
