resource "google_bigquery_dataset" "gemini_enterprise" {
  dataset_id                 = "gemini_enterprise"
  delete_contents_on_destroy = true
  location                   = "US"
  project                    = google_project_service.apis["bigquery.googleapis.com"].project
}

resource "google_bigquery_dataset" "ai_financial_dlp" {
  dataset_id                 = "ai_financial_dlp"
  delete_contents_on_destroy = true
  location                   = "US"
  project                    = google_project_service.apis["bigquery.googleapis.com"].project
}

resource "google_bigquery_table" "gemini_enterprise_analytics" {
  dataset_id          = google_bigquery_dataset.gemini_enterprise.dataset_id
  project             = google_project_service.apis["bigquery.googleapis.com"].project
  table_id            = "analytics"
  deletion_protection = false
}

resource "google_bigquery_table" "xxc_gl_summary" {
  project    = google_bigquery_dataset.ai_financial_dlp.project
  dataset_id = google_bigquery_dataset.ai_financial_dlp.dataset_id
  table_id   = "XXC_GL_SUMMARY"
  schema = jsonencode([
    {name = "journal_header_id", type = "STRING", mode = "NULLABLE"},
    {name = "journal_line_number", type = "INT64", mode = "NULLABLE"},
    {name = "invoice_id", type = "STRING", mode = "NULLABLE"},
    {name = "invoice_number", type = "STRING", mode = "NULLABLE"},
    {name = "gl_code_combination_id", type = "STRING", mode = "NULLABLE"},
    {name = "legal_entity", type = "STRING", mode = "NULLABLE"},
    {name = "location", type = "STRING", mode = "NULLABLE"},
    {name = "department", type = "STRING", mode = "NULLABLE"},
    {name = "account", type = "STRING", mode = "NULLABLE"},
    {name = "sub_account", type = "STRING", mode = "NULLABLE"},
    {name = "account_name", type = "STRING", mode = "NULLABLE"},
    {name = "sub_account_name", type = "STRING", mode = "NULLABLE"},
    {name = "amount", type = "NUMERIC", mode = "NULLABLE"},
    {name = "stat_amount", type = "NUMERIC", mode = "NULLABLE"},
    {name = "currency_code", type = "STRING", mode = "NULLABLE"},
    {name = "ledger_id", type = "INT64", mode = "NULLABLE"},
    {name = "effective_date", type = "DATE", mode = "NULLABLE"},
    {name = "period_name", type = "STRING", mode = "NULLABLE"},
    {name = "journal_posted_date", type = "DATE", mode = "NULLABLE"},
    {name = "journal_category", type = "STRING", mode = "NULLABLE"},
    {name = "journal_source", type = "STRING", mode = "NULLABLE"},
    {name = "line_description", type = "STRING", mode = "NULLABLE"},
    {name = "batch_name", type = "STRING", mode = "NULLABLE"},
    {name = "category", type = "STRING", mode = "NULLABLE"},
    {name = "super_category", type = "STRING", mode = "NULLABLE"},
    {name = "commodity", type = "STRING", mode = "NULLABLE"},
    {name = "vendor_name", type = "STRING", mode = "NULLABLE"},
    {name = "vendor_id", type = "STRING", mode = "NULLABLE"},
    {name = "po_number", type = "STRING", mode = "NULLABLE"},
    {name = "check_id", type = "STRING", mode = "NULLABLE"},
    {name = "check_number", type = "STRING", mode = "NULLABLE"},
    {name = "source_system", type = "STRING", mode = "NULLABLE"},
    {name = "created_at", type = "TIMESTAMP", mode = "NULLABLE"},
    {name = "updated_at", type = "TIMESTAMP", mode = "NULLABLE"},
  ])
}

resource "google_bigquery_table" "xxc_gl_div_reg_fac" {
  project    = google_bigquery_dataset.ai_financial_dlp.project
  dataset_id = google_bigquery_dataset.ai_financial_dlp.dataset_id
  table_id   = "XXC_GL_DIV_REG_FAC"
  schema = jsonencode([
    {name = "facility_id", type = "STRING", mode = "REQUIRED"},
    {name = "facility_description", type = "STRING", mode = "NULLABLE"},
    {name = "facility_common_name", type = "STRING", mode = "NULLABLE"},
    {name = "palmer_vp", type = "STRING", mode = "NULLABLE"},
    {name = "palmer_vp_desc", type = "STRING", mode = "NULLABLE"},
    {name = "group_vp", type = "STRING", mode = "NULLABLE"},
    {name = "group_vp_desc", type = "STRING", mode = "NULLABLE"},
    {name = "division", type = "STRING", mode = "NULLABLE"},
    {name = "division_desc", type = "STRING", mode = "NULLABLE"},
    {name = "region", type = "STRING", mode = "NULLABLE"},
    {name = "region_desc", type = "STRING", mode = "NULLABLE"},
    {name = "facility_type", type = "STRING", mode = "NULLABLE"},
    {name = "legal_entity", type = "STRING", mode = "NULLABLE"},
    {name = "legal_entity_desc", type = "STRING", mode = "NULLABLE"},
    {name = "inactive_date", type = "DATE", mode = "NULLABLE"},
    {name = "is_active", type = "BOOL", mode = "NULLABLE"},
    {name = "accounting_start_date", type = "DATE", mode = "NULLABLE"},
    {name = "accounting_end_date", type = "DATE", mode = "NULLABLE"},
    {name = "denovo_flag", type = "STRING", mode = "NULLABLE"},
    {name = "rollup_flag", type = "STRING", mode = "NULLABLE"},
    {name = "facility_administrator_name", type = "STRING", mode = "NULLABLE"},
    {name = "regional_director_name", type = "STRING", mode = "NULLABLE"},
    {name = "facility_city", type = "STRING", mode = "NULLABLE"},
    {name = "facility_state", type = "STRING", mode = "NULLABLE"},
    {name = "facility_zip_code", type = "STRING", mode = "NULLABLE"},
    {name = "county", type = "STRING", mode = "NULLABLE"},
    {name = "source_system", type = "STRING", mode = "NULLABLE"},
    {name = "created_at", type = "TIMESTAMP", mode = "NULLABLE"},
    {name = "updated_at", type = "TIMESTAMP", mode = "NULLABLE"},
  ])
}

resource "google_bigquery_table" "ap_suppliers" {
  project    = google_bigquery_dataset.ai_financial_dlp.project
  dataset_id = google_bigquery_dataset.ai_financial_dlp.dataset_id
  table_id   = "AP_SUPPLIERS"
  schema = jsonencode([
    {name = "vendor_id", type = "STRING", mode = "REQUIRED"},
    {name = "vendor_number", type = "STRING", mode = "NULLABLE"},
    {name = "supplier_name", type = "STRING", mode = "NULLABLE"},
    {name = "supplier_name_normalized", type = "STRING", mode = "NULLABLE"},
    {name = "vendor_type", type = "STRING", mode = "NULLABLE"},
    {name = "organization_type", type = "STRING", mode = "NULLABLE"},
    {name = "enabled_flag", type = "BOOL", mode = "NULLABLE"},
    {name = "is_active", type = "BOOL", mode = "NULLABLE"},
    {name = "start_date_active", type = "DATE", mode = "NULLABLE"},
    {name = "end_date_active", type = "DATE", mode = "NULLABLE"},
    {name = "hold_flag", type = "BOOL", mode = "NULLABLE"},
    {name = "hold_reason", type = "STRING", mode = "NULLABLE"},
    {name = "hold_all_payments_flag", type = "BOOL", mode = "NULLABLE"},
    {name = "hold_future_payments_flag", type = "BOOL", mode = "NULLABLE"},
    {name = "payment_terms_id", type = "STRING", mode = "NULLABLE"},
    {name = "payment_priority", type = "INT64", mode = "NULLABLE"},
    {name = "invoice_currency_code", type = "STRING", mode = "NULLABLE"},
    {name = "payment_currency_code", type = "STRING", mode = "NULLABLE"},
    {name = "num_1099", type = "STRING", mode = "NULLABLE"},
    {name = "type_1099", type = "STRING", mode = "NULLABLE"},
    {name = "tax_reporting_name", type = "STRING", mode = "NULLABLE"},
    {name = "source_system", type = "STRING", mode = "NULLABLE"},
    {name = "created_at", type = "TIMESTAMP", mode = "NULLABLE"},
    {name = "updated_at", type = "TIMESTAMP", mode = "NULLABLE"},
  ])
}

resource "google_bigquery_table" "ap_invoices_all" {
  project    = google_bigquery_dataset.ai_financial_dlp.project
  dataset_id = google_bigquery_dataset.ai_financial_dlp.dataset_id
  table_id   = "AP_INVOICES_ALL"
  schema = jsonencode([
    {name = "invoice_id", type = "STRING", mode = "REQUIRED"},
    {name = "vendor_id", type = "STRING", mode = "NULLABLE"},
    {name = "vendor_site_id", type = "STRING", mode = "NULLABLE"},
    {name = "invoice_number", type = "STRING", mode = "NULLABLE"},
    {name = "po_header_id", type = "STRING", mode = "NULLABLE"},
    {name = "org_id", type = "STRING", mode = "NULLABLE"},
    {name = "party_id", type = "STRING", mode = "NULLABLE"},
    {name = "party_site_id", type = "STRING", mode = "NULLABLE"},
    {name = "invoice_date", type = "DATE", mode = "NULLABLE"},
    {name = "gl_date", type = "DATE", mode = "NULLABLE"},
    {name = "invoice_received_date", type = "DATE", mode = "NULLABLE"},
    {name = "invoice_amount", type = "NUMERIC", mode = "NULLABLE"},
    {name = "amount_paid", type = "NUMERIC", mode = "NULLABLE"},
    {name = "currency_code", type = "STRING", mode = "NULLABLE"},
    {name = "description", type = "STRING", mode = "NULLABLE"},
    {name = "source", type = "STRING", mode = "NULLABLE"},
    {name = "source_system", type = "STRING", mode = "NULLABLE"},
    {name = "created_at", type = "TIMESTAMP", mode = "NULLABLE"},
    {name = "updated_at", type = "TIMESTAMP", mode = "NULLABLE"},
  ])
}
