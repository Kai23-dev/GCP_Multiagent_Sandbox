variable "resource_labels" {
  description = "Labels to apply to all resources"
  type        = map(string)
}

variable "suffix" {
  description = "A random string suffix to ensure uniqueness"
  type        = string
}

variable "env" {
  description = "Environment name (e.g., p, np, etc.)"
  type        = string
}

variable "folder_id" {
  description = "The GCP folder ID where the project will be created"
  type        = string
}

variable "gcp_billing_account" {
  description = "The GCP billing account ID to associate with the project"
  type        = string
}

variable "region" {
  description = "The GCP region for resources"
  type        = string
  default     = "us-central1"
}

variable "image_tag" {
  type        = string
  description = "The image tag for the nextjs web app."
}

variable "gar_project_id" {
  description = "The GCP project ID where the Artifact Registry is located"
  type        = string
}

variable "gcp_org_id" {
  description = "The GCP organization ID"
  type        = string
}

variable "gitlab_project_path_slug" {
  type        = string
  description = "The GitLab project path slug for storing/retrieving Terraform state."
}

variable "static_env" {
  description = "If its a static env or not"
  type        = bool
  default     = false
}

variable "gemini_enterprise_ldap_groups" {
  description = "List of LDAP groups for Gemini Enterprise access"
  type        = list(string)
  default     = []
}

variable "trace_viewer_image_tag" {
  type        = string
  description = "The image tag for the trace-viewer Cloud Run service."
}

# DNS Configuration for IAP Load Balancers
variable "dns_project_id" {
  description = "The DNS project ID for domain management"
  type        = string
}

variable "public_dns_zone_name" {
  description = "The public DNS zone name"
  type        = string
}

variable "public_dns_name" {
  description = "The public DNS name"
  type        = string
}

variable "private_dns_zone_name" {
  description = "The private DNS zone name"
  type        = string
}

variable "private_dns_name" {
  description = "The private DNS name"
  type        = string
}

# SSL Certificates for IAP Load Balancers
variable "ai_np_davita_com_cert" {
  description = "Path to non-prod DaVita wildcard SSL certificate"
  type        = string
}

variable "ai_np_davita_com_base64_key" {
  description = "Path to base64-encoded non-prod DaVita wildcard SSL key"
  type        = string
}

variable "ai_prod_davita_com_cert" {
  description = "Path to prod DaVita wildcard SSL certificate"
  type        = string
}

variable "ai_prod_davita_com_base64_key" {
  description = "Path to base64-encoded prod DaVita wildcard SSL key"
  type        = string
}
