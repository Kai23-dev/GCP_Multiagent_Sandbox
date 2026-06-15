variable "resource_labels" {
  description = "Labels to apply to all resources"
  type        = map(string)
}

variable "gcp_billing_account" {
  description = "The GCP billing account ID to associate with the project"
  type        = string
}

variable "image_tag" {
  type        = string
  description = "The image tag for the nextjs web app."
}

variable "gcp_org_id" {
  type        = string
  description = "The ID of the Google Cloud organization."
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

variable "trace_viewer_image_tag" {
  type        = string
  description = "The image tag for the trace-viewer Cloud Run service."
}

# SSL Certificates for IAP Load Balancers (from GitLab CI secrets)
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
