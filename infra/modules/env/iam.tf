resource "google_project_iam_member" "cf_access" {
  for_each = toset([
    "roles/run.invoker", # for interacting with the MCP Toolbox
    "roles/iap.httpsResourceAccessor",
    "roles/discoveryengine.user", # required for Farhan and team to setup Gemini enterprise subscriptions
    "roles/aiplatform.user",
  ])
  project = google_project.agent_project.project_id
  role    = each.value
  member  = "group:gcp-cloud-foundations@davita.com"
}

resource "google_project_iam_member" "agentspace_admins_access" {
  for_each = toset([
    "roles/run.invoker", # for interacting with the MCP Toolbox
    "roles/iap.httpsResourceAccessor",
  ])
  project = google_project.agent_project.project_id
  role    = each.value
  member  = "group:gcp-agentspace-admins@davita.com"
}

resource "google_service_account" "web_app" {
  account_id   = "web-app"
  display_name = "Web App Service Account"
  project      = google_project.agent_project.project_id
}

resource "google_project_iam_member" "default_run_service_agent" {
  project = google_project_service.apis["run.googleapis.com"].project
  role    = each.value
  for_each = toset([
    "roles/aiplatform.user",
    "roles/discoveryengine.user",
    "roles/run.invoker",
    "roles/run.serviceAgent",
  ])
  member = google_project_service_identity.run_service_identity.member #"serviceAccount:service-${google_project.agent_project.number}@serverless-robot-prod.iam.gserviceaccount.com"
  depends_on = [
    google_project_service.apis
  ]
}

# IAM permissions for the web app service account
# These allow the service account to call Google Cloud APIs using ADC
resource "google_project_iam_member" "web_app" {
  project = google_project_service.apis["run.googleapis.com"].project
  role    = each.value
  for_each = toset([
    "roles/aiplatform.user",      # Agent Engine & Vertex AI
    "roles/discoveryengine.user", # Discovery Engine agents
    "roles/dialogflow.client",    # Dialogflow CX agents
  ])
  member = "serviceAccount:${google_service_account.web_app.email}"
  depends_on = [
    google_project_service.apis
  ]
}

# Create IAP service identity to ensure it exists before we try to use it
resource "google_project_service_identity" "iap_service_identity" {
  provider = google-beta
  project  = google_project_service.apis["iap.googleapis.com"].project
  service  = "iap.googleapis.com"
}

resource "google_project_service_identity" "run_service_identity" {
  provider = google-beta
  project  = google_project_service.apis["run.googleapis.com"].project
  service  = "run.googleapis.com"
}

resource "google_project_service_identity" "discovery_engine" {
  provider = google-beta
  project  = google_project_service.apis["discoveryengine.googleapis.com"].project
  service  = "discoveryengine.googleapis.com"
}

resource "google_bigquery_dataset_iam_member" "discovery_engine" {
  dataset_id = google_bigquery_dataset.gemini_enterprise.dataset_id
  project    = google_project_service.apis["bigquery.googleapis.com"].project
  role       = "roles/bigquery.dataEditor"
  member     = google_project_service_identity.discovery_engine.member
}

resource "google_project_iam_member" "discvoery_engine" {
  project = google_project_service.apis["discoveryengine.googleapis.com"].project
  role    = each.value
  for_each = toset([
    "roles/discoveryengine.serviceAgent",
    "roles/bigquery.jobUser"
  ])
  member = google_project_service_identity.discovery_engine.member
}

# Grant access to the IAP service account for Cloud Run invocations
resource "google_project_iam_member" "agentspace_iap" {
  project = google_project.agent_project.project_id
  role    = "roles/run.invoker"
  member  = google_project_service_identity.iap_service_identity.member
  depends_on = [
    google_project_service.apis["iap.googleapis.com"],
    google_project_service.apis["run.googleapis.com"],
  ]
}

resource "google_project_iam_member" "robot_access" {
  project = var.gar_project_id
  role    = each.value
  for_each = toset([
    "roles/run.serviceAgent",
  ])
  member = google_project_service_identity.run_service_identity.member #"serviceAccount:service-${google_project.agent_project.number}@serverless-robot-prod.iam.gserviceaccount.com"
  depends_on = [
    google_project_service.apis,
  ]
}

# required for interacting with agent engine
resource "google_project_iam_member" "cf" {
  project = google_project.agent_project.project_id
  role    = each.value
  for_each = toset([
    "roles/aiplatform.user",
    "roles/storage.objectUser",
    "roles/cloudtrace.user",
  ])
  member = "group:gcp-cloud-foundations@davita.com"
}

# required for interacting with agent engine
resource "google_project_iam_member" "base_access_for_ai_strategy_engineers" {
  project = google_project.agent_project.project_id
  role    = each.value
  for_each = {
    for role in [
      "organizations/${var.gcp_org_id}/roles/ITViewer",
      "roles/aiplatform.user",
      "roles/storage.objectUser",
      "roles/run.invoker", # for interacting with the MCP Toolbox
      "roles/iap.httpsResourceAccessor",
      "roles/discoveryengine.user", # required for Farhan and team to setup Gemini enterprise subscriptions
      "roles/cloudtrace.user",
    ] : role => role
  }
  member = "group:gcp-ai-strategy-engineers@davita.com"
}

##################################
# Workforce Identity Pool Access #
##################################

# access for licensed users signing in from the workforce pool to users in CN=gcp-ai-agentspace-users
resource "google_project_iam_member" "discovery_engine_access" {
  project  = google_project.agent_project.project_id
  for_each = toset(var.gemini_enterprise_ldap_groups)
  role     = "roles/discoveryengine.user"
  member   = "principalSet://iam.googleapis.com/locations/global/workforcePools/pingsaml/group/${each.key}"
}

# access for licensed users signing in from the workforce pool to users in CN=gcp-ai-agentspace-users
resource "google_project_iam_member" "aiplatform_access" {
  project  = google_project.agent_project.project_id
  for_each = toset(var.gemini_enterprise_ldap_groups)
  role     = "roles/aiplatform.user"
  member   = "principalSet://iam.googleapis.com/locations/global/workforcePools/pingsaml/group/${each.key}"
}

#######################################
# Gemini Enterprise User Group Access #
#######################################
# required for managing the gemini enterprise instance
resource "google_project_iam_member" "access" {
  for_each = toset([
    "organizations/${var.gcp_org_id}/roles/ITViewer",
    "roles/aiplatform.admin",
    "roles/notebooks.admin",
    "roles/storage.admin",
    "roles/discoveryengine.admin",
    "roles/dialogflow.admin",
    "roles/aiplatform.colabEnterpriseAdmin", # required for setting up agentspace stuff
    "roles/run.invoker",                     # for interacting with the MCP
    "roles/cloudaicompanion.user",
    "roles/iap.httpsResourceAccessor",
  ])

  project = google_project.agent_project.project_id
  role    = each.value
  member  = "group:gcp-agentspace-admins@davita.com"
}

# base user access to project
# resource "google_project_iam_member" "agentspace_users" {
#   for_each = toset([
#     "organizations/${var.gcp_org_id}/roles/ITViewer",
#     "roles/aiplatform.user",
#     "roles/discoveryengine.user",
#     "roles/dialogflow.reader",
#     "roles/cloudaicompanion.user",
#     "roles/iap.httpsResourceAccessor",
#   ])

#   project = google_project.agent_project.project_id
#   role    = each.value
#   member  = "group:gcp-ai-agentspace-users@davita.com"
# }
