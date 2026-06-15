output "project_id" {
  value      = google_project.agent_project.project_id
  depends_on = [google_project_service.apis]
}

output "project_number" {
  value      = google_project.agent_project.number
  depends_on = [google_project_service.apis]
}

output "agent_staging_bucket" {
  value      = google_storage_bucket.agent_bucket.name
  depends_on = [google_project_service.apis]
}

# output "web_app_url" {
#   value = google_cloud_run_v2_service.sco_agents.uri
# }

output "data_source_bucket" {
  value = google_storage_bucket.data_source.name
}

output "table_schemas_bucket" {
  value = google_storage_bucket.table_schemas.name
}

output "is_review" {
  value = local.is_review
}

output "gemini_enterprise_engine_id" {
  value = length(module.agent_auth) > 0 ? module.agent_auth[0].gemini_enterprise_engine_id : ""
}

output "gemini_enterprise_location" {
  value = length(module.agent_auth) > 0 ? module.agent_auth[0].gemini_enterprise_location : ""
}


output "visualizations_bucket" {
  value = google_storage_bucket.visualizations.name
}

output "reasoning_engine_service_agent" {
  value      = local.reasoning_engine_service_agent
  depends_on = [google_project_service.apis]
}

output "oauth_client_secret" {
  value = module.agent_auth[0].oauth_client_secret
}

output "oauth_client_id" {
  value = module.agent_auth[0].oauth_client_id
}