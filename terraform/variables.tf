variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

variable "image" {
  description = "Docker image for Cloud Run (e.g. gcr.io/project/hiring-service:latest)"
  type        = string
}

variable "db_password" {
  description = "Cloud SQL postgres user password"
  type        = string
  sensitive   = true
}

variable "redis_url" {
  description = "Redis Cloud connection URL (redis://default:pass@host:port)"
  type        = string
  sensitive   = true
}

variable "storage_bucket" {
  description = "GCS bucket name for employee CSVs"
  type        = string
  default     = "hiring"
}

variable "invoker_members" {
  description = "IAM members authorized to invoke the service, or [\"allUsers\"] if public"
  type        = list(string)
}
