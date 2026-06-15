locals {
  env_short            = var.env == "default" ? "p" : trimprefix(trimsuffix(lower(substr(var.env, 0, 8)), "-"), "-")
  resource_suffix      = "${local.env_short}-${var.suffix}"
  resource_suffix_long = "${lower(var.env)}-${var.suffix}"

  env_title = terraform.workspace == "default" ? "Prod" : (
    var.static_env ? title(local.env_short) : "Review"
  )

  is_review = local.env_title == "Review"

  resource_labels = merge(var.resource_labels,
    {
      env_name = substr(terraform.workspace, 0, 62)
      repo     = var.gitlab_project_path_slug
    }
  )
  reasoning_engine_service_agent = "service-${google_project.agent_project.number}@gcp-sa-aiplatform-re.iam.gserviceaccount.com"
}

# host project for agent engine
resource "google_project" "agent_project" {
  name            = "SCO Agents ${local.env_title}"
  project_id      = "sco-agents-${local.resource_suffix}"
  folder_id       = var.folder_id
  billing_account = var.gcp_billing_account
  labels          = local.resource_labels
  deletion_policy = "DELETE"
}

# enable required apis
resource "google_project_service" "apis" {
  for_each = toset([
    "aiplatform.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "cloudaicompanion.googleapis.com",
    "cloudtrace.googleapis.com",
    "compute.googleapis.com",
    "dialogflow.googleapis.com",
    "firestore.googleapis.com",
    "discoveryengine.googleapis.com",
    "generativelanguage.googleapis.com",
    "iam.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "bigquery.googleapis.com",
    "storage.googleapis.com",
    "storage-component.googleapis.com",
    "cloudtrace.googleapis.com",
    "servicenetworking.googleapis.com",
    "secretmanager.googleapis.com",
    "iap.googleapis.com",
    "run.googleapis.com",
    "telemetry.googleapis.com",
  ])
  project                    = google_project.agent_project.project_id
  service                    = each.key
  disable_dependent_services = false
  disable_on_destroy         = false
}

# staging bucket for agent engine deployments
resource "google_storage_bucket" "agent_bucket" {
  name                        = "sco-agents-${local.resource_suffix}"
  location                    = var.region
  force_destroy               = true
  labels                      = var.resource_labels
  project                     = google_project.agent_project.project_id
  public_access_prevention    = "enforced"
  uniform_bucket_level_access = true
}

resource "google_storage_bucket" "data_source" {
  name                        = "sco-agents-default-ds-${local.resource_suffix}"
  location                    = var.region
  force_destroy               = true
  labels                      = var.resource_labels
  project                     = google_project.agent_project.project_id
  public_access_prevention    = "enforced"
  uniform_bucket_level_access = true
}

# GCS bucket for storing table schema markdown files
resource "google_storage_bucket" "table_schemas" {
  name                        = "sco-agents-table-schemas-${local.resource_suffix}"
  location                    = var.region
  force_destroy               = true
  labels                      = var.resource_labels
  project                     = google_project.agent_project.project_id
  public_access_prevention    = "enforced"
  uniform_bucket_level_access = true
}

# Upload table schema files to the bucket
resource "google_storage_bucket_object" "table_schemas_folder" {
  for_each = fileset("${path.module}/ai_financial_dlp", "*.md")

  name   = "ai_financial_dlp/${each.value}"
  bucket = google_storage_bucket.table_schemas.name
  source = "${path.module}/ai_financial_dlp/${each.value}"
}

resource "google_storage_bucket" "visualizations" {
  name                        = "sco-agents-visualizations-${local.resource_suffix}"
  location                    = var.region
  force_destroy               = true
  labels                      = var.resource_labels
  project                     = google_project.agent_project.project_id
  public_access_prevention    = "enforced"
  uniform_bucket_level_access = true
}

# Firestore database for trace-viewer agent registry
resource "google_firestore_database" "trace_viewer" {
  project         = google_project_service.apis["firestore.googleapis.com"].project
  name            = "(default)"
  location_id     = var.region
  type            = "FIRESTORE_NATIVE"
  deletion_policy = "DELETE"

  depends_on = [
    google_project_service.apis["firestore.googleapis.com"],
  ]
}

# join shared vpc
# resource "google_compute_shared_vpc_service_project" "this" {
#   service_project = google_project_service.apis["servicenetworking.googleapis.com"].project
#   host_project    = var.vpc_project_id
#   depends_on      = [google_project_service.apis]
# }

module "agent_auth" {
  count                            = 1 # sigh, this isnt needed but removing the count will brick things...
  source                           = "gitlab.gcp.davita.com/ai/google-adk-automation/local//modules/gemini-enterprise"
  version                          = "1.0.1"
  project_id                       = google_project.agent_project.project_id
  project_number                   = google_project.agent_project.number
  reasoning_engine_service_account = local.reasoning_engine_service_agent
}

