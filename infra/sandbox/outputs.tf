output "project_id" {
  value = data.google_project.sandbox.project_id
}

output "dataset_id" {
  value = data.google_bigquery_dataset.ai_financial_dlp.dataset_id
}

output "table_schemas_bucket" {
  value = google_storage_bucket.table_schemas.name
}

output "sandbox_project_number" {
  value = data.google_project.sandbox.number
}