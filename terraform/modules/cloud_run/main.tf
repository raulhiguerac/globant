resource "google_cloud_run_v2_service" "main" {
  name     = "hiring-service"
  location = var.region

  template {
    service_account = var.service_account_email

    volumes {
      name = "cloudsql"
      cloud_sql_instance {
        instances = [var.cloud_sql_connection_name]
      }
    }

    containers {
      image = var.image

      env {
        name  = "STORAGE_BUCKET"
        value = var.bucket_name
      }

      env {
        name  = "GCS_PROJECT"
        value = var.project_id
      }

      env {
        name = "DATABASE_URL"
        value_source {
          secret_key_ref {
            secret  = var.secret_database_url_id
            version = "latest"
          }
        }
      }

      env {
        name = "REDIS_URL"
        value_source {
          secret_key_ref {
            secret  = var.secret_redis_url_id
            version = "latest"
          }
        }
      }

      volume_mounts {
        name       = "cloudsql"
        mount_path = "/cloudsql"
      }
    }
  }
}

resource "google_cloud_run_v2_service_iam_member" "public" {
  name     = google_cloud_run_v2_service.main.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}
