# Resources first created by hand on 16 Nov 2026 (Azure CLI / Synapse Studio), adopted
# into the state on the next `terraform apply` instead of being recreated.
# These blocks can be deleted once that apply has run.

import {
  to = azurerm_monitor_action_group.alerts
  id = "${azurerm_resource_group.main.id}/providers/Microsoft.Insights/actionGroups/ag-${var.project}-alerts"
}

import {
  to = azurerm_monitor_metric_alert.adf_failed_runs
  id = "${azurerm_resource_group.main.id}/providers/Microsoft.Insights/metricAlerts/alert-adf-failed-runs"
}

# Synapse role assignment ID, from:
#   az synapse role assignment list --workspace-name <ws> --assignee <ADF principal ID> --query "[].id"
import {
  to = azurerm_synapse_role_assignment.adf
  id = "${azurerm_synapse_workspace.main.id}|627ab5f1-2ef9-4900-896e-356dfafd1b60"
}
