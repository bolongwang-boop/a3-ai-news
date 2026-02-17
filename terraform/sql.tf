# ============================================================================
# NETWORKING - VPC for Cloud SQL private IP
# ============================================================================

resource "google_compute_network" "vpc" {
  name                    = "${local.service_name}-vpc"
  project                 = local.project_id
  auto_create_subnetworks = false

  depends_on = [google_project_service.apis["servicenetworking.googleapis.com"]]
}

resource "google_compute_subnetwork" "subnet" {
  name          = "${local.service_name}-subnet"
  project       = local.project_id
  region        = local.region
  network       = google_compute_network.vpc.id
  ip_cidr_range = "10.0.0.0/24"
}

# Reserve IP range for private services (Cloud SQL)
resource "google_compute_global_address" "private_ip_range" {
  name          = "${local.service_name}-private-ip"
  project       = local.project_id
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.vpc.id
}

resource "google_service_networking_connection" "private_vpc" {
  network                 = google_compute_network.vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_range.name]
}

# VPC access connector for Cloud Run -> Cloud SQL
resource "google_vpc_access_connector" "connector" {
  name    = "${local.service_name}-connector"
  project = local.project_id
  region  = local.region

  subnet {
    name = google_compute_subnetwork.subnet.name
  }

  min_instances = 2
  max_instances = 3

  depends_on = [google_project_service.apis["vpcaccess.googleapis.com"]]
}

# ============================================================================
# CLOUD SQL - PostgreSQL instance
# ============================================================================

resource "google_sql_database_instance" "postgres" {
  name             = "${local.service_name}-db"
  project          = local.project_id
  region           = local.region
  database_version = local.db_version

  settings {
    tier              = local.db_tier
    availability_type = "ZONAL"
    disk_size         = 10
    disk_type         = "PD_SSD"
    disk_autoresize   = true

    ip_configuration {
      ipv4_enabled                                  = false
      private_network                               = google_compute_network.vpc.id
      enable_private_path_for_google_cloud_services = true
    }

    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
      start_time                     = "03:00"
      transaction_log_retention_days = 7

      backup_retention_settings {
        retained_backups = 7
      }
    }

    maintenance_window {
      day  = 7 # Sunday
      hour = 4
    }
  }

  deletion_protection = true

  depends_on = [
    google_project_service.apis["sqladmin.googleapis.com"],
    google_service_networking_connection.private_vpc,
  ]
}

resource "google_sql_database" "ai_news" {
  name     = local.db_name
  instance = google_sql_database_instance.postgres.name
  project  = local.project_id
}

resource "google_sql_user" "ainews" {
  name     = local.db_user
  instance = google_sql_database_instance.postgres.name
  project  = local.project_id
  password = random_password.db_password.result
}

resource "random_password" "db_password" {
  length  = 32
  special = false
}

# Store the database URL in Secret Manager
resource "google_secret_manager_secret_version" "database_url" {
  secret      = google_secret_manager_secret.database_url.id
  secret_data = "postgresql+asyncpg://${local.db_user}:${random_password.db_password.result}@${google_sql_database_instance.postgres.private_ip_address}/${local.db_name}"
}

# Allow Cloud Run service account to connect to Cloud SQL
resource "google_project_iam_member" "sql_client" {
  project = local.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.ai_news.email}"
}
