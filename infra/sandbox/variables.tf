variable "project_id" {
  description = "The GCP project ID for the sandbox project. Must be globally unique."
  type        = string
}

variable "project_name" {
  description = "The display name for the sandbox project."
  type        = string
  default     = "SCO Agents Sandbox"
}

variable "folder_id" {
  description = "The GCP folder ID where the sandbox project will be created."
  type        = string
}

variable "billing_account" {
  description = "The GCP billing account ID to attach to the sandbox project."
  type        = string
}

variable "region" {
  description = "The GCP region for sandbox resources."
  type        = string
  default     = "us-central1"
}

variable "dataset_location" {
  description = "The BigQuery dataset location."
  type        = string
  default     = "US"
}
