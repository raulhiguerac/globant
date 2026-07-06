output "service_url" {
  value       = module.cloud_run.url
  description = "Cloud Run service URL"
}

output "bucket_name" {
  value       = module.gcs.bucket_name
  description = "GCS bucket for employee CSVs"
}
