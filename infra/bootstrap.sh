#!/usr/bin/env bash
# One-time setup, run BEFORE the first `terraform init`:
#   1. registers the Azure resource providers the project needs
#   2. creates the storage account that holds the remote Terraform state
#   3. writes infra/backend.hcl, used by `terraform init -backend-config=backend.hcl`
#
# Usage: ./infra/bootstrap.sh [location]   (default: francecentral)
# Safe to re-run: existing resources are reused.
set -euo pipefail

LOCATION="${1:-francecentral}"
RG="rg-velib-tfstate"
CONTAINER="tfstate"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_FILE="$SCRIPT_DIR/backend.hcl"

echo "Subscription: $(az account show --query name -o tsv)"

for ns in Microsoft.Storage Microsoft.KeyVault Microsoft.DataFactory Microsoft.Synapse Microsoft.Sql Microsoft.Consumption; do
  az provider register --namespace "$ns" --output none
done
echo "Resource providers registered."

az group create --name "$RG" --location "$LOCATION" --output none

# Reuse the state account if it already exists, otherwise create one with a unique name.
SA=$(az storage account list --resource-group "$RG" --query "[0].name" -o tsv)
if [[ -z "$SA" ]]; then
  SA="sttfstate$(openssl rand -hex 4)"
  az storage account create \
    --name "$SA" --resource-group "$RG" --location "$LOCATION" \
    --sku Standard_LRS --kind StorageV2 \
    --min-tls-version TLS1_2 --allow-blob-public-access false \
    --output none
fi

# Access the state with Entra ID (no storage keys): the current user needs a data role.
ME=$(az ad signed-in-user show --query id -o tsv)
SA_ID=$(az storage account show --name "$SA" --resource-group "$RG" --query id -o tsv)
az role assignment create --assignee-object-id "$ME" --assignee-principal-type User \
  --role "Storage Blob Data Contributor" --scope "$SA_ID" --output none 2>/dev/null || true

# Role assignments can take a minute to propagate.
for _ in {1..12}; do
  if az storage container create --name "$CONTAINER" --account-name "$SA" --auth-mode login --output none 2>/dev/null; then
    break
  fi
  echo "Waiting for role propagation..."
  sleep 10
done

cat >"$BACKEND_FILE" <<EOF
resource_group_name  = "$RG"
storage_account_name = "$SA"
container_name       = "$CONTAINER"
key                  = "velib-platform.tfstate"
use_azuread_auth     = true
EOF

echo "Done. Backend config written to $BACKEND_FILE"
