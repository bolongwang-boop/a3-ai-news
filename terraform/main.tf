# Terraform configuration for a3-ai-news Cloud Run service
#
# This creates resources for:
# - Cloud Run service for the AI News API
# - Service account with required IAM roles
# - Secret Manager for API keys and database credentials
# - Cloud SQL PostgreSQL instance
# - VPC connector for Cloud Run -> Cloud SQL
#
# Access paths:
#   n8n         -> a3-auth-proxy -> Cloud Run (OIDC)
#   Internal    -> Cloud Run (IAM)

terraform {
  required_version = ">= 1.0"

  backend "gcs" {
    bucket = "a3-ai-news-tfstate"
    prefix = "terraform/state"
  }

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.0"
    }
  }
}

provider "google" {
  project = local.project_id
  region  = local.region
}

# Enable required APIs
resource "google_project_service" "apis" {
  for_each = toset(local.project_services)

  project            = local.project_id
  service            = each.key
  disable_on_destroy = false
}

# ============================================================================
# SERVICE ACCOUNT
# ============================================================================

resource "google_service_account" "ai_news" {
  account_id   = local.service_name
  display_name = "AI News API Service Account"
  project      = local.project_id
}

# ============================================================================
# SECRET MANAGER
# ============================================================================

variable "newsapi_key" {
  description = "NewsAPI.org API key"
  type        = string
  sensitive   = true
}

resource "google_secret_manager_secret" "newsapi_key" {
  secret_id = "${local.service_name}-newsapi-key"
  project   = local.project_id

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis["secretmanager.googleapis.com"]]
}

resource "google_secret_manager_secret_version" "newsapi_key" {
  secret      = google_secret_manager_secret.newsapi_key.id
  secret_data = var.newsapi_key
}

resource "google_secret_manager_secret" "database_url" {
  secret_id = "${local.service_name}-database-url"
  project   = local.project_id

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis["secretmanager.googleapis.com"]]
}

# Allow service account to access secrets
resource "google_secret_manager_secret_iam_member" "newsapi_key_access" {
  secret_id = google_secret_manager_secret.newsapi_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.ai_news.email}"
}

resource "google_secret_manager_secret_iam_member" "database_url_access" {
  secret_id = google_secret_manager_secret.database_url.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.ai_news.email}"
}

# ============================================================================
# CLOUD RUN SERVICE
# ============================================================================

resource "google_cloud_run_v2_service" "ai_news" {
  name     = local.service_name
  location = local.region
  project  = local.project_id

  template {
    service_account = google_service_account.ai_news.email

    vpc_access {
      connector = google_vpc_access_connector.connector.id
      egress    = "PRIVATE_RANGES_ONLY"
    }

    scaling {
      min_instance_count = 0
      max_instance_count = 10
    }

    containers {
      image = "gcr.io/${local.project_id}/${local.service_name}"

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
        name = "AINEWS_NEWSAPI_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.newsapi_key.secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "AINEWS_DATABASE_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.database_url.secret_id
            version = "latest"
          }
        }
      }

      env {
        name  = "AINEWS_ENABLE_PERSISTENCE"
        value = "true"
      }
    }
  }

  # No unauthenticated access - auth-proxy uses OIDC to call this service
  ingress = "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"

  deletion_protection = false

  depends_on = [
    google_project_service.apis["run.googleapis.com"],
    google_secret_manager_secret_iam_member.newsapi_key_access,
    google_secret_manager_secret_iam_member.database_url_access,
  ]
}

# ============================================================================
# IAM - Allow auth-proxy service account to invoke this Cloud Run service
# ============================================================================

resource "google_cloud_run_v2_service_iam_member" "auth_proxy_invoker" {
  project  = local.project_id
  location = local.region
  name     = google_cloud_run_v2_service.ai_news.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:a3-auth-proxy@${local.project_id}.iam.gserviceaccount.com"
}
