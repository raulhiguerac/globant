resource "google_project_service" "apis" {
  for_each = toset([
    "secretmanager.googleapis.com",
    "sqladmin.googleapis.com",
    "run.googleapis.com",
  ])
  project            = var.project_id
  service            = each.key
  disable_on_destroy = true
}

resource "google_project_service" "apis_no_disable" {
  for_each = toset([
    "storage.googleapis.com",
  ])
  project            = var.project_id
  service            = each.key
  disable_on_destroy = false
}

resource "time_sleep" "api_propagation" {
  create_duration = "30s"
  depends_on      = [google_project_service.apis, google_project_service.apis_no_disable]
}

resource "google_service_account" "app" {
  account_id   = "hiring-service-sa"
  display_name = "Hiring Service"
  depends_on   = [time_sleep.api_propagation]
}

resource "google_project_iam_member" "cloudsql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.app.email}"
}

module "secret_manager" {
  source                = "./modules/secret_manager"
  project_id            = var.project_id
  database_url          = "postgresql://admin:${var.db_password}@/app_db?host=/cloudsql/${var.project_id}:${var.region}:hiring-db"
  redis_url             = var.redis_url
  service_account_email = google_service_account.app.email

  depends_on = [google_service_account.app, time_sleep.api_propagation]
}

module "gcs" {
  source                = "./modules/gcs"
  project_id            = var.project_id
  region                = var.region
  bucket_name           = var.storage_bucket
  service_account_email = google_service_account.app.email

  depends_on = [module.secret_manager]
}

module "cloud_sql" {
  source      = "./modules/cloud_sql"
  project_id  = var.project_id
  region      = var.region
  db_password = var.db_password

  depends_on = [module.secret_manager]
}

# module "cloud_run" {
#   source                    = "./modules/cloud_run"
#   project_id                = var.project_id
#   region                    = var.region
#   image                     = var.image
#   service_account_email     = google_service_account.app.email
#   cloud_sql_connection_name = module.cloud_sql.connection_name
#   bucket_name               = module.gcs.bucket_name
#   secret_database_url_id    = module.secret_manager.database_url_secret_id
#   secret_redis_url_id       = module.secret_manager.redis_url_secret_id
#
#   depends_on = [module.gcs, module.cloud_sql, module.secret_manager]
# }
