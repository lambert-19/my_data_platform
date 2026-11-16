# Email alert when a run of the ingestion pipeline fails (pl_ingest_velib).
resource "azurerm_monitor_action_group" "alerts" {
  name                = "ag-${var.project}-alerts"
  resource_group_name = azurerm_resource_group.main.name
  short_name          = "${var.project}alert"
  tags                = var.tags

  dynamic "email_receiver" {
    for_each = toset(var.alert_emails)
    content {
      name          = split("@", email_receiver.value)[0]
      email_address = email_receiver.value
    }
  }
}

resource "azurerm_monitor_metric_alert" "adf_failed_runs" {
  name                = "alert-adf-failed-runs"
  resource_group_name = azurerm_resource_group.main.name
  scopes              = [azurerm_data_factory.main.id]
  description         = "Velib ingestion pipeline failed (pl_ingest_velib)"
  severity            = 2
  frequency           = "PT5M"
  window_size         = "PT15M"
  tags                = var.tags

  criteria {
    metric_namespace = "Microsoft.DataFactory/factories"
    metric_name      = "PipelineFailedRuns"
    aggregation      = "Total"
    operator         = "GreaterThan"
    threshold        = 0
  }

  action {
    action_group_id = azurerm_monitor_action_group.alerts.id
  }
}
