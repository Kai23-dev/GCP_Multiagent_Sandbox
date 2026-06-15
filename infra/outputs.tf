output "gcp" {
  value = {
    env      = module.agent_project
    spend_iq = module.spend_iq_agent
  }
}
