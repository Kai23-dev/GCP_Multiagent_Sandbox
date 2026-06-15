# =============================================================================
# Trace Viewer IAP-Protected Load Balancer
# Provides secure access via Ping SAML authentication (Workforce Identity)
# =============================================================================

locals {
  # LDAP groups for trace-viewer access
  # Using full DN format: CN=group-name,OU=GCP,OU=Security,OU=Groups,OU=DVA-US,DC=DAVITA,DC=Corp
  ad_group_suffix = "OU=GCP,OU=Security,OU=Groups,OU=DVA-US,DC=DAVITA,DC=Corp"

  trace_viewer_ldap_groups = [
    "CN=gcp-cloud-foundations,${local.ad_group_suffix}",
    "CN=gcp-ai-strategy-engineers,${local.ad_group_suffix}",
    "CN=gcp-agentspace-admins,${local.ad_group_suffix}",
    "CN=gcp-ai-agentspace-users,${local.ad_group_suffix}",
  ]

  # SSL cert selection based on environment
  pre_crt = terraform.workspace != "default" ? var.ai_np_davita_com_cert : var.ai_prod_davita_com_cert
  pre_key = terraform.workspace != "default" ? var.ai_np_davita_com_base64_key : var.ai_prod_davita_com_base64_key
  crt     = file(local.pre_crt)
  key     = base64decode(file(local.pre_key))
}

# IAP-Protected Load Balancer for Trace Viewer
module "trace_viewer_iap_lb" {
  source  = "gitlab.gcp.davita.com/shared-services/iap-protected-lb-with-workforce-identity/local"
  version = "1.5.0"

  # Project Configuration
  project_id     = google_project.agent_project.project_id
  project_number = google_project.agent_project.number
  suffix         = var.suffix
  env            = local.env_short

  # Cloud Run Service
  service_name = google_cloud_run_v2_service.trace_viewer.name
  region       = var.region

  # DNS Configuration
  dns_project_id        = var.dns_project_id
  public_dns_name       = var.public_dns_name
  public_dns_zone_name  = var.public_dns_zone_name
  private_dns_name      = var.private_dns_name
  private_dns_zone_name = var.private_dns_zone_name

  # IAP Configuration with Workforce Identity Federation
  workforce_identity_pool_id              = "pingsaml"
  iap_https_resource_accessor_ldap_groups = local.trace_viewer_ldap_groups

  # SSL Certificate (DaVita wildcard cert)
  create_google_managed_certificate = false
  davita_wildcard_cert_crt          = local.crt
  davita_wildcard_cert_key          = local.key

  depends_on = [
    google_project_service.apis["run.googleapis.com"],
    google_project_service.apis["iap.googleapis.com"],
    google_project_service_identity.iap_service_identity,
    google_project_iam_member.agentspace_iap,
    google_project_iam_member.default_run_service_agent,
    google_project_iam_member.robot_access,
    google_project_iam_member.trace_viewer,
    google_cloud_run_v2_service.trace_viewer,
  ]
}
