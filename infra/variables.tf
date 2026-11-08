variable "subscription_id" {
  description = "Azure subscription ID (az account show --query id -o tsv)."
  type        = string
}

variable "location" {
  description = "Azure region. Must be allowed by the Azure for Students policy."
  type        = string
  default     = "francecentral"
}

variable "project" {
  description = "Short project name used in resource names (lowercase letters only)."
  type        = string
  default     = "velib"

  validation {
    condition     = can(regex("^[a-z]{3,8}$", var.project))
    error_message = "project must be 3-8 lowercase letters (storage account naming rules)."
  }
}

variable "collaborators" {
  description = "Entra ID UPNs of team members who get access to the project resources."
  type        = list(string)
  default     = []
}

variable "spark_auto_pause_minutes" {
  description = "Idle minutes before the Spark pool pauses (cost control)."
  type        = number
  default     = 15
}

variable "budget_amount" {
  description = "Monthly budget in the subscription currency; alerts at 50/80/100%."
  type        = number
  default     = 50
}

variable "budget_contact_emails" {
  description = "Emails that receive budget alerts."
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Tags applied to all resources."
  type        = map(string)
  default = {
    project = "my-data-platform"
    module  = "5CLOU"
  }
}
