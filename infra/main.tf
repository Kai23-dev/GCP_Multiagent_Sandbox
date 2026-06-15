data "consul_keys" "join" {
  key {
    name = "bootstrap" # for the bootstrap data in consul containing folder ids
    path = "gitlab/terraform_outputs/v2/ai/ai-bootstrap/default"
  }
  key {
    name = "program" # for the program data in consul containing the shared vpc, gar, and other 2nd tier shared ai program infra
    path = "gitlab/terraform_outputs/v2/ai/ai-program/default"
  }
  key {
    name = "sco-kb"
    path = "gitlab/terraform_outputs/v2/ai/applications/sco-knowledge-base/${local.consul_env_switch}"
  }
  key {
    name = "mcp-server"
    path = "gitlab/terraform_outputs/v2/ai/model-context/ai-mcp-services/${local.consul_env_switch}"
  }
}

# setup some local variables for use in the infra to keep from repeating code
locals {
  consul_env_switch        = contains(["stage", "dev", "default"], terraform.workspace) ? terraform.workspace : "dev" # if its review, map to dev otherwise use the workspace  env                        = terraform.workspace == "default" ? "Prod" : "Review"
  p_or_np                  = terraform.workspace == "default" && var.static_env == false ? "p" : "np"
  join_bootstrap           = jsondecode(data.consul_keys.join.var["bootstrap"]).outputs.env
  pipeline_service_account = local.join_bootstrap[local.p_or_np].service_accounts.pipeline
  join_program             = jsondecode(data.consul_keys.join.var["program"]).outputs
  program_data             = local.join_program.gcp.us_central1[local.p_or_np]
  program_data_np          = local.join_program.gcp.us_central1["np"]
  vpc                      = local.program_data.vpc
  vpc_np                   = local.program_data_np.vpc
  gce_subnet               = local.vpc.gce
  gce_subnet_np            = local.vpc_np.gce
  gar                      = local.program_data.gar
  gar_np                   = local.program_data_np.gar
  join_sco_kb              = jsondecode(data.consul_keys.join.var["sco-kb"]).outputs.gcp.us_central1
  join_mcp_server          = jsondecode(data.consul_keys.join.var["mcp-server"]).outputs.gcp.env

  # DNS configuration for IAP load balancers
  dns                   = local.program_data.dns
  dns_project_id        = local.program_data.dns.private_zone.project_id
  private_dns_zone_name = local.program_data.dns.private_zone.name
  private_dns_name      = local.program_data.dns.private_zone.dns_name
  public_dns_zone_name  = local.program_data.dns.public_zone.name
  public_dns_name       = local.program_data.dns.public_zone.dns_name

  # gemini enterprise cannot be enable any other way than by hand, and to make agents available in gemini enterprise
  # we have to authorize them, which requires passing in a ref to gemini enterprise
  #  we only should od this for envs we have set this up for, otherwise it will fail
  gemini_enterprise_instance_map = {
    default = module.agent_project.gemini_enterprise_engine_id
  }

  gemini_enterprise_instance = lookup(local.gemini_enterprise_instance_map, terraform.workspace, local.gemini_enterprise_instance_map.default)

  # Only register with Gemini Enterprise in static environments (dev, stage, prod), not review
  enable_gemini_enterprise_registration = contains(["dev", "stage", "default"], terraform.workspace)

  default_agent_resource_configs = {
    memory        = "8Gi"
    cpu           = "2"
    concurrency   = 9
    min_instances = 1
    max_instances = 100
  }

}

# generate a suffix to ensure unique project ids and bucket names
resource "random_string" "suffix" {
  length  = 4
  upper   = false
  special = false
}

# create projects and infra for SCO agents
module "agent_project" {
  source                        = "./modules/env"
  env                           = terraform.workspace == "default" ? "p" : terraform.workspace
  suffix                        = random_string.suffix.result
  folder_id                     = local.join_bootstrap[local.p_or_np].gcp_folder_id
  gcp_billing_account           = var.gcp_billing_account
  region                        = "us-central1"
  resource_labels               = var.resource_labels
  image_tag                     = var.image_tag
  gar_project_id                = local.gar.project_id
  gcp_org_id                    = var.gcp_org_id
  gitlab_project_path_slug      = var.gitlab_project_path_slug
  static_env                    = var.static_env
  gemini_enterprise_ldap_groups = local.ldap_groups # set in infra/gemini-enterprise-access.tf
  trace_viewer_image_tag        = var.trace_viewer_image_tag

  # DNS and SSL cert configuration for IAP load balancers
  dns_project_id                = local.dns_project_id
  private_dns_zone_name         = local.private_dns_zone_name
  public_dns_zone_name          = local.public_dns_zone_name
  private_dns_name              = local.private_dns_name
  public_dns_name               = local.public_dns_name
  ai_np_davita_com_cert         = var.ai_np_davita_com_cert
  ai_np_davita_com_base64_key   = var.ai_np_davita_com_base64_key
  ai_prod_davita_com_cert       = var.ai_prod_davita_com_cert
  ai_prod_davita_com_base64_key = var.ai_prod_davita_com_base64_key
}

