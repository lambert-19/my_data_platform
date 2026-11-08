data "azurerm_client_config" "current" {}

data "azurerm_subscription" "current" {}

# Team members other than the person running Terraform.
data "azuread_user" "collaborators" {
  for_each            = toset(var.collaborators)
  user_principal_name = each.value
}

# Suffix that makes globally unique names (storage, Key Vault, ADF, Synapse).
resource "random_string" "suffix" {
  length  = 6
  upper   = false
  special = false
}

locals {
  suffix = random_string.suffix.result
  # Object IDs of every human who works on the project.
  team_object_ids = merge(
    { me = data.azurerm_client_config.current.object_id },
    { for upn, u in data.azuread_user.collaborators : upn => u.object_id },
  )
  collaborator_object_ids = { for upn, u in data.azuread_user.collaborators : upn => u.object_id }
}

resource "azurerm_resource_group" "main" {
  name     = "rg-${var.project}-platform"
  location = var.location
  tags     = var.tags
}
