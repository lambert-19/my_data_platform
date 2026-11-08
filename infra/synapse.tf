# Processing: Spark pool for PySpark notebooks + built-in serverless SQL for Power BI.
resource "azurerm_synapse_workspace" "main" {
  name                                 = "synw-${var.project}-${local.suffix}"
  resource_group_name                  = azurerm_resource_group.main.name
  location                             = azurerm_resource_group.main.location
  storage_data_lake_gen2_filesystem_id = azurerm_storage_data_lake_gen2_filesystem.synapse.id

  # Entra ID only: no SQL password to manage or leak.
  azuread_authentication_only = true

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}

# Entra ID admin of the serverless SQL endpoint (the person running Terraform).
resource "azurerm_synapse_workspace_aad_admin" "main" {
  synapse_workspace_id = azurerm_synapse_workspace.main.id
  login                = "AzureAD Admin"
  object_id            = data.azurerm_client_config.current.object_id
  tenant_id            = data.azurerm_client_config.current.tenant_id
}

# Lets Azure services (ADF, Power BI Service) reach the workspace.
resource "azurerm_synapse_firewall_rule" "azure_services" {
  name                 = "AllowAllWindowsAzureIps"
  synapse_workspace_id = azurerm_synapse_workspace.main.id
  start_ip_address     = "0.0.0.0"
  end_ip_address       = "0.0.0.0"
}

# Team members work from changing networks; access is still protected by Entra ID only.
resource "azurerm_synapse_firewall_rule" "clients" {
  name                 = "AllowAllClients"
  synapse_workspace_id = azurerm_synapse_workspace.main.id
  start_ip_address     = "0.0.0.0"
  end_ip_address       = "255.255.255.255"
}

resource "azurerm_synapse_spark_pool" "main" {
  name                 = "spark${var.project}"
  synapse_workspace_id = azurerm_synapse_workspace.main.id
  node_size_family     = "MemoryOptimized"
  node_size            = "Small"
  spark_version        = "3.4"

  # Smallest possible pool: 3 nodes x 4 vCores.
  node_count = 3

  auto_pause {
    delay_in_minutes = var.spark_auto_pause_minutes
  }

  tags = var.tags
}
