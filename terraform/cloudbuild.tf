# ============================================================================
# CLOUD BUILD - GitHub trigger for continuous deployment
# ============================================================================

# Fetch project number for the default Cloud Build service account
data "google_project" "project" {
  project_id = local.project_id
}

# Cloud Build trigger: deploy on every push to main
# NOTE: Requires a GitHub connection first. Create one at:
#   https://console.cloud.google.com/cloud-build/repositories/2nd-gen?project=a3-team-481403
# Then uncomment and set the repository field.
#
# resource "google_cloudbuild_trigger" "deploy" {
#   name     = "${local.service_name}-deploy"
#   project  = local.project_id
#   location = local.region
#
#   repository_event_config {
#     repository = "projects/${local.project_id}/locations/${local.region}/connections/CONNECTION_NAME/repositories/${local.github_repo}"
#     push {
#       branch = "^main$"
#     }
#   }
#
#   filename = "cloudbuild.yaml"
#
#   substitutions = {
#     _REGION          = local.region
#     _SERVICE_NAME    = local.service_name
#     _SERVICE_ACCOUNT = google_service_account.ai_news.email
#   }
#
#   depends_on = [google_project_service.apis["cloudbuild.googleapis.com"]]
# }

# ============================================================================
# IAM - Grant Cloud Build service account permissions to deploy
# ============================================================================

# 2nd-gen Cloud Build triggers use the App Engine default service account
# (<project-id>@appspot.gserviceaccount.com), not the legacy Cloud Build SA.
locals {
  cloudbuild_sa = "serviceAccount:${local.project_id}@appspot.gserviceaccount.com"
}

# Cloud Build needs to deploy to Cloud Run
resource "google_project_iam_member" "cloudbuild_run_admin" {
  project = local.project_id
  role    = "roles/run.admin"
  member  = local.cloudbuild_sa
}

# Cloud Build needs to act as the Cloud Run service account
resource "google_service_account_iam_member" "cloudbuild_act_as" {
  service_account_id = google_service_account.ai_news.name
  role               = "roles/iam.serviceAccountUser"
  member             = local.cloudbuild_sa
}

# Cloud Build needs to access secrets for database migrations
resource "google_secret_manager_secret_iam_member" "cloudbuild_database_url_access" {
  secret_id = google_secret_manager_secret.database_url.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = local.cloudbuild_sa
}

# Cloud Build needs VPC access for database migrations
resource "google_project_iam_member" "cloudbuild_vpc_access" {
  project = local.project_id
  role    = "roles/vpcaccess.user"
  member  = local.cloudbuild_sa
}
