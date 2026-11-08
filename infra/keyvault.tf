# Secrets store. Access is controlled with Azure RBAC (see rbac.tf), not access policies.
resource "azurerm_key_vault" "main" {
  name                       = "kv-${var.project}-${local.suffix}"
  resource_group_name        = azurerm_resource_group.main.name
  location                   = azurerm_resource_group.main.location
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  rbac_authorization_enabled = true
  soft_delete_retention_days = 7
  purge_protection_enabled   = false

  tags = var.tags
}
