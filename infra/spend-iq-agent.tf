module "spend_iq_agent" {
  source             = "gitlab.gcp.davita.com/ai/google-adk-automation/local"
  version            = "1.0.2"
  project_id         = module.agent_project.project_id
  agent_id           = "spend-iq-agent"
  agent_display_name = "SpendIQ Agent"
  location           = "us-central1"

  additional_env_vars = {
    GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY         = "true"
    OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT = "true"
    MCP_URL                                            = local.join_mcp_server.mcp_core_url
    GENAI_MCP_URL                                      = local.join_mcp_server.mcp_server_genai_toolbox_url
    SCO_KB_PROJECT_ID                                  = local.join_sco_kb.project_id
    # Sub-agent resource names for ReasoningEngine references
    AUDITOR_AGENT_RESOURCE                 = module.auditor_agent.reasoning_engine_name
    BUYER_AGENT_RESOURCE                   = module.buyer_agent.reasoning_engine_name
    TREND_AGENT_RESOURCE                   = module.trend_agent.reasoning_engine_name
    SUPPLIER_CLASSIFICATION_AGENT_RESOURCE = module.supplier_classification_agent.reasoning_engine_name
    CONTRACT_INTELLIGENCE_AGENT_RESOURCE   = module.contract_intelligence_agent.reasoning_engine_name
    FINANCIAL_LEAKAGE_AGENT_RESOURCE       = module.financial_leakage_agent.reasoning_engine_name
  }

  resource_limits = {
    memory = local.default_agent_resource_configs.memory
    cpu    = local.default_agent_resource_configs.cpu
  }

  min_instances         = local.default_agent_resource_configs.min_instances
  max_instances         = local.default_agent_resource_configs.max_instances
  container_concurrency = local.default_agent_resource_configs.concurrency
  # Agent deployment
  gemini_enterprise_engine_id     = local.gemini_enterprise_instance
  gemini_enterprise_location      = "us"
  register_with_gemini_enterprise = local.enable_gemini_enterprise_registration

  additional_agent_roles = [
    "roles/discoveryengine.user", # For Gemini Enterprise
  ]
  depends_on = [
    module.auditor_agent,
    module.buyer_agent,
    module.trend_agent,
    module.supplier_classification_agent,
    module.contract_intelligence_agent,
    module.financial_leakage_agent,
  ]

  # Agent deployment
  agent_source_path = "./agents/spend_iq_agent"
  staging_bucket    = module.agent_project.agent_staging_bucket
}

resource "google_project_iam_member" "spend_iq_agent_access" {
  project = local.join_mcp_server.project_id
  role    = each.value
  for_each = toset([
    "roles/run.invoker",
    "roles/aiplatform.user",
    "roles/bigquery.jobUser",
  ])
  member = "serviceAccount:${module.spend_iq_agent.service_account_email}"
}

resource "google_project_iam_member" "spend_iq_agent_bq_job_user" {
  project = local.join_sco_kb.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${module.spend_iq_agent.service_account_email}"
}
