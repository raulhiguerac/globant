resource "google_sql_database_instance" "main" {
  name             = "hiring-db"
  database_version = "POSTGRES_15"
  region           = var.region

  settings {
    tier = "db-f1-micro"

    ip_configuration {
      ipv4_enabled = true
      authorized_networks {
        value = "0.0.0.0/0"
        name  = "allow-all"
      }
    }

    deletion_protection_enabled = false
  }

  deletion_protection = false
}

resource "google_sql_database" "app" {
  name     = "app_db"
  instance = google_sql_database_instance.main.name
}

resource "google_sql_user" "app" {
  name     = "admin"
  instance = google_sql_database_instance.main.name
  password = var.db_password
}
