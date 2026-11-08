# Email alerts when spending reaches 50%, 80% and 100% of the monthly budget.
resource "azurerm_consumption_budget_resource_group" "main" {
  count             = length(var.budget_contact_emails) > 0 ? 1 : 0
  name              = "budget-${var.project}"
  resource_group_id = azurerm_resource_group.main.id
  amount            = var.budget_amount
  time_grain        = "Monthly"

  time_period {
    start_date = formatdate("YYYY-MM-01'T'00:00:00Z", plantimestamp())
  }

  dynamic "notification" {
    for_each = [50, 80, 100]
    content {
      enabled        = true
      threshold      = notification.value
      operator       = "GreaterThanOrEqualTo"
      threshold_type = "Actual"
      contact_emails = var.budget_contact_emails
    }
  }

  lifecycle {
    # start_date must not move on every plan.
    ignore_changes = [time_period]
  }
}
