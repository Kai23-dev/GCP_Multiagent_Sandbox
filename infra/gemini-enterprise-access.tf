
# this chunk of code sets up access for users to Gemini Enterprise based on LDAP groups. We will be using LDAP only for access to Gemini Enterprise.
# most of the userbase that needs access will not have a normal Google account due to them being clinical or business in nature
locals {
  ldap_groups = [
    "CN=gcp-ai-agentspace-users,OU=GCP,OU=Security,OU=Groups,OU=DVA-US,DC=DAVITA,DC=Corp",
    "CN=gcp-agentspace-admins,OU=GCP,OU=Security,OU=Groups,OU=DVA-US,DC=DAVITA,DC=Corp",
    # ... add more groups as needed
  ]
}
