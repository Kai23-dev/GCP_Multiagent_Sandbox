module "validation_agent" {
  source     = "gitlab.gcp.davita.com/ai/google-adk-automation/local"
  version    = "1.0.2"
  project_id = module.agent_project.project_id
  agent_id   = "validation-agent"
  location   = "us-central1"

  additional_env_vars = {
    GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY         = "true"
    OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT = "true"
    GENAI_MCP_URL                                      = local.join_mcp_server.mcp_server_genai_toolbox_url
    SCO_KB_PROJECT_ID                                  = local.join_sco_kb.project_id
    TABLE_SCHEMA_GCS_BUCKET                            = module.agent_project.table_schemas_bucket
    TABLE_SCHEMA_GCS_PREFIX                            = "table/"
  }

  resource_limits = {
    memory = "4Gi"
    cpu    = "2"
  }
  min_instances         = 1
  max_instances         = 10
  container_concurrency = 5

  # Agent deployment
  agent_source_path = "./agents/validation_agent"
  staging_bucket    = module.agent_project.agent_staging_bucket
  depends_on        = [module.sql_execution_agent]
}

resource "google_project_iam_member" "validation_agent_access" {
  project = local.join_mcp_server.project_id
  role    = each.value
  for_each = toset([
    "roles/run.invoker",
    "roles/aiplatform.user",
    "roles/bigquery.jobUser",
  ])
  member = "serviceAccount:${module.validation_agent.service_account_email}"
}

resource "google_project_iam_member" "validation_agent_bq_job_user" {
  project = local.join_sco_kb.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${module.validation_agent.service_account_email}"
}

resource "google_storage_bucket_iam_member" "validation_agent_table_schemas_reader" {
  bucket = module.agent_project.table_schemas_bucket
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${module.validation_agent.service_account_email}"
}
