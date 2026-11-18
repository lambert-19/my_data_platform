# Infrastructure (Terraform)

Deploys the whole Azure platform in `francecentral`:

| Resource | Name pattern | Role |
|---|---|---|
| Resource group | `rg-velib-platform` | Holds everything below |
| ADLS Gen2 | `stvelib<suffix>` | Containers `bronze`, `silver`, `gold` (+ `synapse` for the workspace) |
| Key Vault | `kv-velib-<suffix>` | Secrets (RBAC mode) |
| Data Factory | `adf-velib-<suffix>` | Ingestion, managed identity |
| Synapse workspace | `synw-velib-<suffix>` | Entra ID only, serverless SQL |
| Spark pool | `sparkvelib` | 3 × Small nodes, auto-pause 15 min |
| Budget | `budget-velib` | Email alerts at 50 / 80 / 100 % |
| Action group + metric alert | `ag-velib-alerts`, `alert-adf-failed-runs` | Email when an ADF pipeline run fails |

Access (all through Entra ID, no keys or SQL passwords):

- **Team members** (`collaborators` + whoever runs `apply`): Contributor on the resource group, Storage Blob Data Contributor on the lake, Key Vault Administrator, Synapse Administrator.
- **ADF and Synapse managed identities**: Storage Blob Data Contributor on the lake, Key Vault Secrets User.
- **ADF managed identity**: Synapse Administrator on the workspace, to run the processing notebook.

The Terraform state is stored remotely in `rg-velib-tfstate` (created by `bootstrap.sh`).

## Deploy

Prerequisites: Azure CLI (`az login`), Terraform ≥ 1.6, Owner on the subscription.

```bash
cd infra
./bootstrap.sh                                  # once: providers + remote state + backend.hcl
cp terraform.tfvars.example terraform.tfvars    # then fill it in
terraform init -backend-config=backend.hcl
terraform plan
terraform apply                                 # ~10 min (Synapse is the slowest)
terraform output                                # names and URLs to share with the team
```

The alert and ADF's Synapse role were first created by hand (16 Nov 2026), then adopted into the state by the blocks in [`imports.tf`](imports.tf) during the 17 Nov `apply`. Those blocks are now no-ops and the file can be deleted.

Two `lifecycle.ignore_changes` rules avoid drift on things set outside Terraform: the ADF GitHub link (configured from ADF Studio) and the default SQL admin login Azure adds to the Synapse workspace (it would otherwise force a replacement).

Not managed here: the Microsoft Fabric workspace, Lakehouse and report (created in the Fabric UI on a trial capacity, see [powerbi/README.md](../powerbi/README.md)).

CI (`.github/workflows/ci.yml`) runs `terraform fmt -check` and `terraform validate` on every push, without a backend or Azure credentials.

## Destroy (after the evaluation)

```bash
terraform destroy
az group delete --name rg-velib-tfstate --yes   # remote state storage
```
