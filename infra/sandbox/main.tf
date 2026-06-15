data "google_project" "sandbox" {
  project_id = var.project_id
}

resource "google_project_service" "apis" {
  for_each = toset([
    "aiplatform.googleapis.com",
    "artifactregistry.googleapis.com",
    "bigquery.googleapis.com",
    "cloudbuild.googleapis.com",
    "iam.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "storage.googleapis.com",
    "firestore.googleapis.com",
  ])

  project = data.google_project.sandbox.project_id
  service = each.key
}

resource "google_storage_bucket" "table_schemas" {
  name          = "${var.project_id}-table-schemas"
  location      = var.region
  force_destroy = true
  project       = data.google_project.sandbox.project_id

  labels = {
    env  = "sandbox"
    repo = "sco-agents"
  }

  uniform_bucket_level_access = true
}

resource "google_storage_bucket_object" "table_schemas" {
  for_each     = fileset("${path.module}/../modules/env/ai_financial_dlp", "*.md")
  name         = "ai_financial_dlp/${each.value}"
  bucket       = google_storage_bucket.table_schemas.name
  source       = "${path.module}/../modules/env/ai_financial_dlp/${each.value}"
  content_type = "text/markdown"
}

data "google_bigquery_dataset" "ai_financial_dlp" {
  project    = var.project_id
  dataset_id = "ai_financial_dlp"
}

resource "google_bigquery_dataset" "gemini_enterprise" {
  project    = data.google_project.sandbox.project_id
  dataset_id = "gemini_enterprise"
  location   = var.dataset_location

  delete_contents_on_destroy = true
}

resource "google_bigquery_table" "xxc_gl_summary" {
  project    = data.google_bigquery_dataset.ai_financial_dlp.project
  dataset_id = data.google_bigquery_dataset.ai_financial_dlp.dataset_id
  table_id   = "XXC_GL_SUMMARY"

  schema = jsonencode([
    { name = "journal_header_id", type = "STRING", mode = "NULLABLE" },
    { name = "journal_line_number", type = "INT64", mode = "NULLABLE" },
    { name = "invoice_id", type = "STRING", mode = "NULLABLE" },
    { name = "invoice_number", type = "STRING", mode = "NULLABLE" },
    { name = "gl_code_combination_id", type = "STRING", mode = "NULLABLE" },
    { name = "legal_entity", type = "STRING", mode = "NULLABLE" },
    { name = "location", type = "STRING", mode = "NULLABLE" },
    { name = "department", type = "STRING", mode = "NULLABLE" },
    { name = "account", type = "STRING", mode = "NULLABLE" },
    { name = "sub_account", type = "STRING", mode = "NULLABLE" },
    { name = "account_name", type = "STRING", mode = "NULLABLE" },
    { name = "sub_account_name", type = "STRING", mode = "NULLABLE" },
    { name = "amount", type = "NUMERIC", mode = "NULLABLE" },
    { name = "stat_amount", type = "NUMERIC", mode = "NULLABLE" },
    { name = "currency_code", type = "STRING", mode = "NULLABLE" },
    { name = "ledger_id", type = "INT64", mode = "NULLABLE" },
    { name = "effective_date", type = "DATE", mode = "NULLABLE" },
    { name = "period_name", type = "STRING", mode = "NULLABLE" },
    { name = "journal_posted_date", type = "DATE", mode = "NULLABLE" },
    { name = "journal_category", type = "STRING", mode = "NULLABLE" },
    { name = "journal_source", type = "STRING", mode = "NULLABLE" },
    { name = "line_description", type = "STRING", mode = "NULLABLE" },
    { name = "batch_name", type = "STRING", mode = "NULLABLE" },
    { name = "category", type = "STRING", mode = "NULLABLE" },
    { name = "super_category", type = "STRING", mode = "NULLABLE" },
    { name = "commodity", type = "STRING", mode = "NULLABLE" },
    { name = "vendor_name", type = "STRING", mode = "NULLABLE" },
    { name = "vendor_id", type = "STRING", mode = "NULLABLE" },
    { name = "po_number", type = "STRING", mode = "NULLABLE" },
    { name = "check_id", type = "STRING", mode = "NULLABLE" },
    { name = "check_number", type = "STRING", mode = "NULLABLE" },
    { name = "source_system", type = "STRING", mode = "NULLABLE" },
    { name = "created_at", type = "TIMESTAMP", mode = "NULLABLE" },
    { name = "updated_at", type = "TIMESTAMP", mode = "NULLABLE" },
  ])
  lifecycle {
    prevent_destroy = true
    ignore_changes  = all
  }
}

resource "google_bigquery_table" "xxc_gl_div_reg_fac" {
  project    = data.google_bigquery_dataset.ai_financial_dlp.project
  dataset_id = data.google_bigquery_dataset.ai_financial_dlp.dataset_id
  table_id   = "XXC_GL_DIV_REG_FAC"

  schema = jsonencode([
    { name = "facility_id", type = "STRING", mode = "REQUIRED" },
    { name = "facility_description", type = "STRING", mode = "NULLABLE" },
    { name = "facility_common_name", type = "STRING", mode = "NULLABLE" },
    { name = "palmer_vp", type = "STRING", mode = "NULLABLE" },
    { name = "palmer_vp_desc", type = "STRING", mode = "NULLABLE" },
    { name = "group_vp", type = "STRING", mode = "NULLABLE" },
    { name = "group_vp_desc", type = "STRING", mode = "NULLABLE" },
    { name = "division", type = "STRING", mode = "NULLABLE" },
    { name = "division_desc", type = "STRING", mode = "NULLABLE" },
    { name = "region", type = "STRING", mode = "NULLABLE" },
    { name = "region_desc", type = "STRING", mode = "NULLABLE" },
    { name = "facility_type", type = "STRING", mode = "NULLABLE" },
    { name = "legal_entity", type = "STRING", mode = "NULLABLE" },
    { name = "legal_entity_desc", type = "STRING", mode = "NULLABLE" },
    { name = "inactive_date", type = "DATE", mode = "NULLABLE" },
    { name = "is_active", type = "BOOL", mode = "NULLABLE" },
    { name = "accounting_start_date", type = "DATE", mode = "NULLABLE" },
    { name = "accounting_end_date", type = "DATE", mode = "NULLABLE" },
    { name = "denovo_flag", type = "STRING", mode = "NULLABLE" },
    { name = "rollup_flag", type = "STRING", mode = "NULLABLE" },
    { name = "facility_administrator_name", type = "STRING", mode = "NULLABLE" },
    { name = "regional_director_name", type = "STRING", mode = "NULLABLE" },
    { name = "facility_city", type = "STRING", mode = "NULLABLE" },
    { name = "facility_state", type = "STRING", mode = "NULLABLE" },
    { name = "facility_zip_code", type = "STRING", mode = "NULLABLE" },
    { name = "county", type = "STRING", mode = "NULLABLE" },
    { name = "source_system", type = "STRING", mode = "NULLABLE" },
    { name = "created_at", type = "TIMESTAMP", mode = "NULLABLE" },
    { name = "updated_at", type = "TIMESTAMP", mode = "NULLABLE" },
  ])
  lifecycle {
    prevent_destroy = true
    ignore_changes  = all
  }
}

resource "google_bigquery_table" "ap_suppliers" {
  project    = data.google_bigquery_dataset.ai_financial_dlp.project
  dataset_id = data.google_bigquery_dataset.ai_financial_dlp.dataset_id
  table_id   = "AP_SUPPLIERS"

  schema = jsonencode([
    { name = "vendor_id", type = "STRING", mode = "REQUIRED" },
    { name = "vendor_number", type = "STRING", mode = "NULLABLE" },
    { name = "supplier_name", type = "STRING", mode = "NULLABLE" },
    { name = "supplier_name_normalized", type = "STRING", mode = "NULLABLE" },
    { name = "vendor_type", type = "STRING", mode = "NULLABLE" },
    { name = "organization_type", type = "STRING", mode = "NULLABLE" },
    { name = "enabled_flag", type = "BOOL", mode = "NULLABLE" },
    { name = "is_active", type = "BOOL", mode = "NULLABLE" },
    { name = "start_date_active", type = "DATE", mode = "NULLABLE" },
    { name = "end_date_active", type = "DATE", mode = "NULLABLE" },
    { name = "hold_flag", type = "BOOL", mode = "NULLABLE" },
    { name = "hold_reason", type = "STRING", mode = "NULLABLE" },
    { name = "hold_all_payments_flag", type = "BOOL", mode = "NULLABLE" },
    { name = "hold_future_payments_flag", type = "BOOL", mode = "NULLABLE" },
    { name = "payment_terms_id", type = "STRING", mode = "NULLABLE" },
    { name = "payment_priority", type = "INT64", mode = "NULLABLE" },
    { name = "invoice_currency_code", type = "STRING", mode = "NULLABLE" },
    { name = "payment_currency_code", type = "STRING", mode = "NULLABLE" },
    { name = "num_1099", type = "STRING", mode = "NULLABLE" },
    { name = "type_1099", type = "STRING", mode = "NULLABLE" },
    { name = "tax_reporting_name", type = "STRING", mode = "NULLABLE" },
    { name = "source_system", type = "STRING", mode = "NULLABLE" },
    { name = "created_at", type = "TIMESTAMP", mode = "NULLABLE" },
    { name = "updated_at", type = "TIMESTAMP", mode = "NULLABLE" },
  ])
  lifecycle {
    prevent_destroy = true
    ignore_changes  = all
  }
}

resource "google_bigquery_table" "ap_invoices_all" {
  project    = data.google_bigquery_dataset.ai_financial_dlp.project
  dataset_id = data.google_bigquery_dataset.ai_financial_dlp.dataset_id
  table_id   = "AP_INVOICES_ALL"

  schema = jsonencode([
    { name = "invoice_id", type = "STRING", mode = "REQUIRED" },
    { name = "vendor_id", type = "STRING", mode = "NULLABLE" },
    { name = "vendor_site_id", type = "STRING", mode = "NULLABLE" },
    { name = "invoice_number", type = "STRING", mode = "NULLABLE" },
    { name = "po_header_id", type = "STRING", mode = "NULLABLE" },
    { name = "org_id", type = "STRING", mode = "NULLABLE" },
    { name = "party_id", type = "STRING", mode = "NULLABLE" },
    { name = "party_site_id", type = "STRING", mode = "NULLABLE" },
    { name = "invoice_date", type = "DATE", mode = "NULLABLE" },
    { name = "gl_date", type = "DATE", mode = "NULLABLE" },
    { name = "invoice_received_date", type = "DATE", mode = "NULLABLE" },
    { name = "invoice_amount", type = "NUMERIC", mode = "NULLABLE" },
    { name = "amount_paid", type = "NUMERIC", mode = "NULLABLE" },
    { name = "currency_code", type = "STRING", mode = "NULLABLE" },
    { name = "description", type = "STRING", mode = "NULLABLE" },
    { name = "source", type = "STRING", mode = "NULLABLE" },
    { name = "source_system", type = "STRING", mode = "NULLABLE" },
    { name = "created_at", type = "TIMESTAMP", mode = "NULLABLE" },
    { name = "updated_at", type = "TIMESTAMP", mode = "NULLABLE" },
  ])
  lifecycle {
    prevent_destroy = true
    ignore_changes  = all
  }
}