# ---------- People ----------

# Collaborators can see and manage every resource of the project.
resource "azurerm_role_assignment" "rg_collaborators" {
  for_each             = local.collaborator_object_ids
  scope                = azurerm_resource_group.main.id
  role_definition_name = "Contributor"
  principal_id         = each.value
  principal_type       = "User"
}

# Read/write data in the lake (Contributor alone does not grant data access).
resource "azurerm_role_assignment" "lake_team" {
  for_each             = local.team_object_ids
  scope                = azurerm_storage_account.lake.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = each.value
  principal_type       = "User"
}

resource "azurerm_role_assignment" "kv_team" {
  for_each             = local.team_object_ids
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Administrator"
  principal_id         = each.value
  principal_type       = "User"
}

# Synapse has its own RBAC: without this, collaborators cannot open notebooks in Synapse Studio.
# The person running Terraform is already Synapse Administrator as the workspace creator.
resource "azurerm_synapse_role_assignment" "collaborators" {
  for_each             = local.collaborator_object_ids
  synapse_workspace_id = azurerm_synapse_workspace.main.id
  role_name            = "Synapse Administrator"
  principal_id         = each.value
  principal_type       = "User"

  depends_on = [azurerm_synapse_firewall_rule.clients]
}

# ---------- Managed identities ----------

resource "azurerm_role_assignment" "lake_adf" {
  scope                = azurerm_storage_account.lake.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_data_factory.main.identity[0].principal_id
  principal_type       = "ServicePrincipal"
}

resource "azurerm_role_assignment" "lake_synapse" {
  scope                = azurerm_storage_account.lake.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_synapse_workspace.main.identity[0].principal_id
  principal_type       = "ServicePrincipal"
}

resource "azurerm_role_assignment" "kv_adf" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_data_factory.main.identity[0].principal_id
  principal_type       = "ServicePrincipal"
}

resource "azurerm_role_assignment" "kv_synapse" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_synapse_workspace.main.identity[0].principal_id
  principal_type       = "ServicePrincipal"
}

# ADF launches the Synapse processing notebook (activity RunProcessingNotebook).
# Synapse has its own RBAC, separate from Azure RBAC.
resource "azurerm_synapse_role_assignment" "adf" {
  synapse_workspace_id = azurerm_synapse_workspace.main.id
  role_name            = "Synapse Administrator"
  principal_id         = azurerm_data_factory.main.identity[0].principal_id
  principal_type       = "ServicePrincipal"

  depends_on = [azurerm_synapse_firewall_rule.clients]
}
