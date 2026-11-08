# Ingestion orchestrator. Its managed identity reads Key Vault and writes to the lake.
# Pipelines themselves are versioned in /adf through ADF Studio's Git integration (step 3).
resource "azurerm_data_factory" "main" {
  name                = "adf-${var.project}-${local.suffix}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}
