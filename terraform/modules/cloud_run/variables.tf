variable "project_id" {
  type = string
}

variable "region" {
  type = string
}

variable "image" {
  type = string
}

variable "service_account_email" {
  type = string
}

variable "cloud_sql_connection_name" {
  type = string
}

variable "bucket_name" {
  type = string
}

variable "secret_database_url_id" {
  type = string
}

variable "secret_redis_url_id" {
  type = string
}

variable "invoker_members" {
  description = "IAM members authorized to invoke the service, or [\"allUsers\"] if public"
  type        = list(string)
}
