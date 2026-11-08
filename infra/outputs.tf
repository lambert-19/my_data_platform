output "resource_group" {
  value = azurerm_resource_group.main.name
}

output "storage_account" {
  description = "Data lake account. Paths: abfss://<layer>@<account>.dfs.core.windows.net/"
  value       = azurerm_storage_account.lake.name
}

output "lake_dfs_endpoint" {
  value = azurerm_storage_account.lake.primary_dfs_endpoint
}

output "key_vault" {
  value = azurerm_key_vault.main.name
}

output "data_factory" {
  value = azurerm_data_factory.main.name
}

output "synapse_workspace" {
  value = azurerm_synapse_workspace.main.name
}

output "synapse_studio_url" {
  value = "https://web.azuresynapse.net?workspace=${azurerm_synapse_workspace.main.id}"
}

output "synapse_serverless_sql_endpoint" {
  description = "Server to use in Power BI (DirectQuery)."
  value       = "${azurerm_synapse_workspace.main.name}-ondemand.sql.azuresynapse.net"
}

output "spark_pool" {
  value = azurerm_synapse_spark_pool.main.name
}
