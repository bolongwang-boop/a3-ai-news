output "service_url" {
  description = "URL of the deployed Cloud Run service"
  value       = google_cloud_run_v2_service.ai_news.uri
}

output "service_account_email" {
  description = "Service account email for the AI News API"
  value       = google_service_account.ai_news.email
}

output "newsapi_key_secret_id" {
  description = "Secret Manager secret ID for the NewsAPI key"
  value       = google_secret_manager_secret.newsapi_key.secret_id
}

output "database_instance_name" {
  description = "Cloud SQL instance name"
  value       = google_sql_database_instance.postgres.name
}

output "database_private_ip" {
  description = "Private IP address of the Cloud SQL instance"
  value       = google_sql_database_instance.postgres.private_ip_address
}

output "database_url_secret_id" {
  description = "Secret Manager secret ID for the database URL"
  value       = google_secret_manager_secret.database_url.secret_id
}

output "vpc_connector_name" {
  description = "VPC access connector for Cloud Run"
  value       = google_vpc_access_connector.connector.name
}
