# Trace Viewer — Cloud Run service for visualizing agent OpenTelemetry traces
# Uses Cloud Trace API (read) and Cloud Logging API (read) to display
# distributed traces across the SCO Agent Engine

# Service account for the trace-viewer Cloud Run service
resource "google_service_account" "trace_viewer" {
  account_id   = "trace-viewer"
  display_name = "Trace Viewer Service Account"
  project      = google_project.agent_project.project_id
}

# IAM roles for the trace-viewer service account
# Needs read access to Cloud Trace, Cloud Logging, and Agent Engine metadata
resource "google_project_iam_member" "trace_viewer" {
  project = google_project_service.apis["run.googleapis.com"].project
  role    = each.value
  for_each = toset([
    "roles/cloudtrace.user",   # Read traces from Cloud Trace
    "roles/logging.viewer",    # Read logs from Cloud Logging
    "roles/aiplatform.viewer", # View Agent Engine metadata
    "roles/monitoring.viewer", # View monitoring metrics
    "roles/datastore.user",    # Read/write Firestore for agent registry
  ])
  member = "serviceAccount:${google_service_account.trace_viewer.email}"
  depends_on = [
    google_project_service.apis
  ]
}

# Cloud Run service for the trace-viewer Next.js app
resource "google_cloud_run_v2_service" "trace_viewer" {
  provider            = google-beta
  name                = "trace-viewer-${var.env}"
  location            = var.region
  deletion_protection = false
  ingress             = "INGRESS_TRAFFIC_ALL"
  project             = google_project_service.apis["run.googleapis.com"].project

  template {
    service_account = google_service_account.trace_viewer.email

    scaling {
      min_instance_count = 0
      max_instance_count = 5
    }

    containers {
      image = var.trace_viewer_image_tag

      ports {
        container_port = 3100
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
        cpu_idle = true
      }

      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = google_project.agent_project.project_id
      }
      env {
        name  = "GOOGLE_CLOUD_LOCATION"
        value = var.region
      }
      env {
        name  = "NODE_ENV"
        value = "production"
      }
      env {
        name  = "AGENT_ENV"
        value = var.env == "p" ? "production" : var.env
      }
      env {
        name  = "FIRESTORE_DATABASE"
        value = "(default)"
      }
      env {
        name  = "AGENT_REGISTRY_COLLECTION"
        value = "trace_viewer_config"
      }

      startup_probe {
        tcp_socket {
          port = 3100
        }
        initial_delay_seconds = 10
        timeout_seconds       = 5
        period_seconds        = 10
        failure_threshold     = 5
      }

      liveness_probe {
        http_get {
          path = "/"
          port = 3100
        }
        timeout_seconds   = 5
        period_seconds    = 30
        failure_threshold = 3
      }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  depends_on = [
    google_project_service.apis["run.googleapis.com"],
    google_project_iam_member.default_run_service_agent,
    google_project_iam_member.robot_access,
    google_project_iam_member.trace_viewer,
    google_firestore_database.trace_viewer,
  ]
}

# Grant Cloud Foundations group invoker access to the trace-viewer service
resource "google_cloud_run_v2_service_iam_member" "trace_viewer_cf_invoker" {
  project  = google_project.agent_project.project_id
  location = var.region
  name     = google_cloud_run_v2_service.trace_viewer.name
  role     = "roles/run.invoker"
  member   = "group:gcp-cloud-foundations@davita.com"
}

# Grant AI Strategy Engineers invoker access to the trace-viewer service
resource "google_cloud_run_v2_service_iam_member" "trace_viewer_ai_engineers_invoker" {
  project  = google_project.agent_project.project_id
  location = var.region
  name     = google_cloud_run_v2_service.trace_viewer.name
  role     = "roles/run.invoker"
  member   = "group:gcp-ai-strategy-engineers@davita.com"
}
