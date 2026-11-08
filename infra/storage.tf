# ADLS Gen2 data lake (hierarchical namespace) with the medallion layers.
resource "azurerm_storage_account" "lake" {
  name                     = "st${var.project}${local.suffix}"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  account_kind             = "StorageV2"
  is_hns_enabled           = true
  min_tls_version          = "TLS1_2"

  allow_nested_items_to_be_public = false
  # Everyone (people, ADF, Synapse) authenticates with Entra ID.
  shared_access_key_enabled = false

  tags = var.tags
}

resource "azurerm_storage_data_lake_gen2_filesystem" "layers" {
  for_each           = toset(["bronze", "silver", "gold"])
  name               = each.key
  storage_account_id = azurerm_storage_account.lake.id

  depends_on = [azurerm_role_assignment.lake_team]
}

# Default filesystem required by the Synapse workspace (logs, temp files, libraries).
resource "azurerm_storage_data_lake_gen2_filesystem" "synapse" {
  name               = "synapse"
  storage_account_id = azurerm_storage_account.lake.id

  depends_on = [azurerm_role_assignment.lake_team]
}
