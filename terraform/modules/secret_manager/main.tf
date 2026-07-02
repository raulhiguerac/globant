resource "google_secret_manager_secret" "database_url" {
  secret_id = "hiring-database-url"

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "database_url" {
  secret      = google_secret_manager_secret.database_url.id
  secret_data = var.database_url
}

resource "google_secret_manager_secret" "redis_url" {
  secret_id = "hiring-redis-url"

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "redis_url" {
  secret      = google_secret_manager_secret.redis_url.id
  secret_data = var.redis_url
}

resource "google_secret_manager_secret_iam_member" "sa_database_url" {
  secret_id = google_secret_manager_secret.database_url.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${var.service_account_email}"
}

resource "google_secret_manager_secret_iam_member" "sa_redis_url" {
  secret_id = google_secret_manager_secret.redis_url.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${var.service_account_email}"
}
