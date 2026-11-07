# My Data Platform : Scale

Plateforme de données quasi temps réel sur Microsoft Azure (module 5CLOU).

**Équipe :** Ibrahima Ndaw · Saer Diene

## Architecture

```
API source → Azure Data Factory → ADLS Gen2 (bronze → silver → gold)
           → Azure Synapse (PySpark + SQL serverless) → Power BI (DirectQuery)
Transverse : Key Vault · identités managées · Terraform
```

_Schéma détaillé : à venir dans `docs/`._

## Organisation du repo

| Dossier | Contenu |
|---|---|
| `infra/` | Terraform (azurerm + microsoft/fabric) |
| `adf/` | Pipelines Azure Data Factory (intégration Git) |
| `synapse/` | Notebooks PySpark et scripts SQL serverless |
| `src/data_platform_project/` | Fonctions Python réutilisables |
| `tests/` | Tests unitaires pytest |
| `powerbi/` | Rapport `.pbix` et captures |
| `docs/` | Architecture, guide de déploiement, slides |

## Développement local

Prérequis : Python 3.13 et [uv](https://docs.astral.sh/uv/).

```bash
uv sync              # installer les dépendances
uv run pytest        # lancer les tests
uv run ruff check .  # lint
uv run black .       # formatage
```

## Déploiement

_À compléter (Terraform, ADF, Synapse, Power BI)._

## Documentation projet

- [Cahier des charges](CAHIER_DES_CHARGES.md)
- [TODO](TODO.md)
