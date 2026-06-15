module "auditor_agent" {
  source     = "gitlab.gcp.davita.com/ai/google-adk-automation/local"
  version    = "1.0.2"
  project_id = module.agent_project.project_id
  agent_id   = "auditor-agent"
  location   = "us-central1"

  additional_env_vars = {
    GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY         = "true"
    OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT = "true"
    GENAI_MCP_URL                                      = local.join_mcp_server.mcp_server_genai_toolbox_url
    SCO_KB_PROJECT_ID                                  = local.join_sco_kb.project_id
    SQL_GENERATION_AGENT_RESOURCE                      = module.sql_generation_agent.reasoning_engine_name
    VALIDATION_AGENT_RESOURCE                          = module.validation_agent.reasoning_engine_name
    SQL_EXECUTION_AGENT_RESOURCE                       = module.sql_execution_agent.reasoning_engine_name
  }

  resource_limits = {
    memory = local.default_agent_resource_configs.memory
    cpu    = local.default_agent_resource_configs.cpu
  }

  min_instances         = local.default_agent_resource_configs.min_instances
  max_instances         = local.default_agent_resource_configs.max_instances
  container_concurrency = local.default_agent_resource_configs.concurrency

  # Agent deployment
  agent_source_path               = "./agents/auditor_agent"
  staging_bucket                  = module.agent_project.agent_staging_bucket
  gemini_enterprise_location      = "us"
  gemini_enterprise_engine_id     = local.gemini_enterprise_instance
  register_with_gemini_enterprise = local.enable_gemini_enterprise_registration
  additional_agent_roles = [
    "roles/discoveryengine.user", # For Gemini Enterprise
  ]
  depends_on = [
    module.sql_generation_agent,
    module.sql_execution_agent,
    module.validation_agent,
    module.contract_intelligence_agent,
  ]
}

resource "google_project_iam_member" "auditor_agent_access" {
  project = local.join_mcp_server.project_id
  role    = each.value
  for_each = toset([
    "roles/run.invoker",
    "roles/aiplatform.user",
    "roles/bigquery.jobUser",
  ])
  member = "serviceAccount:${module.auditor_agent.service_account_email}"
}

resource "google_project_iam_member" "auditor_agent_bq_job_user" {
  project = local.join_sco_kb.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${module.auditor_agent.service_account_email}"
}
