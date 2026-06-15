module "contract_intelligence_agent" {
  source     = "gitlab.gcp.davita.com/ai/google-adk-automation/local"
  version    = "1.0.2"
  project_id = module.agent_project.project_id
  agent_id   = "contract-intelligence-agent"
  location   = "us-central1"

  additional_env_vars = {
    GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY         = "true"
    OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT = "true"
    # MCP server for RAG / GraphRAG contract document tools
    MCP_URL = local.join_mcp_server.mcp_core_url
    # GenAI Toolbox for BigQuery SQL tools (ssi-toolset)
    GENAI_MCP_URL     = local.join_mcp_server.mcp_server_genai_toolbox_url
    SCO_KB_PROJECT_ID = local.join_sco_kb.project_id
    # Default 15 calls/60s is too tight for 5 concurrent queries sharing one
    # rate limiter — causes 429s that force flash-lite fallback (+35s each).
    GEMINI_RATE_LIMIT_MAX_CALLS = "40"
  }

  resource_limits = {
    memory = "4Gi"
    cpu    = "2"
  }

  min_instances         = 1
  max_instances         = 10
  container_concurrency = 5

  # Agent deployment
  agent_source_path               = "./agents/contract_intelligence_agent"
  staging_bucket                  = module.agent_project.agent_staging_bucket
  gemini_enterprise_engine_id     = local.gemini_enterprise_instance
  gemini_enterprise_location      = "us"
  register_with_gemini_enterprise = local.enable_gemini_enterprise_registration

  additional_agent_roles = [
    "roles/discoveryengine.user", # For Gemini Enterprise
  ]
  depends_on = [module.visualization_agent]
}

resource "google_project_iam_member" "contract_intelligence_agent_access" {
  project = local.join_mcp_server.project_id
  role    = each.value
  for_each = toset([
    "roles/run.invoker",
    "roles/aiplatform.user",
    "roles/bigquery.jobUser",
  ])
  member = "serviceAccount:${module.contract_intelligence_agent.service_account_email}"
}

resource "google_project_iam_member" "contract_intelligence_agent_bq_job_user" {
  project = local.join_sco_kb.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${module.contract_intelligence_agent.service_account_email}"
}
