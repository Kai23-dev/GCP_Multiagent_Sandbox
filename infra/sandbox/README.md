# SCO Agents Sandbox

This folder contains a self-contained sandbox Terraform configuration for a lightweight GCP environment.

It is designed to:
- create a sandbox GCP project
- enable BigQuery, Storage, AI Platform, and related APIs
- create `ai_financial_dlp` and `gemini_enterprise` BigQuery datasets
- upload markdown table schema files to a GCS bucket
- create core tables required for financial leakage / trend exploration

## Steps

1. Copy the example variable file:
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   ```
2. Update `terraform.tfvars` with your `project_id`, `folder_id`, and `billing_account`.
3. From `infra/sandbox`:
   ```bash
   terraform init
   terraform apply
   ```
4. Load sample rows:
   ```bash
   python ../../scripts/load_sandbox_bq_data.py --project <PROJECT_ID>
   ```

## Notes

- This sandbox root is intentionally separate from the repo's GitLab CI/production infra.
- It does not currently deploy Vertex AI agents because the agent source directories are not present in this repository.
- If you add the missing `agents/` source folders, the same project can be extended to deploy the SQL generation, validation, SQL execution, and financial leakage agents.
