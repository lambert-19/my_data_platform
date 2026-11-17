# Ingestion orchestrator. Its managed identity reads Key Vault and writes to the lake.
# Pipelines themselves are versioned in this repo through ADF Studio's Git integration.
resource "azurerm_data_factory" "main" {
  name                = "adf-${var.project}-${local.suffix}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags

  lifecycle {
    # The GitHub link is configured from ADF Studio (it needs an interactive GitHub
    # OAuth login); without this, every apply would remove it.
    ignore_changes = [github_configuration, vsts_configuration]
  }
}
