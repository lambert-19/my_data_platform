# My Data Platform : Scale

Plateforme de données quasi temps réel sur Microsoft Azure (module 5CLOU), alimentée par la disponibilité des stations **Vélib' Métropole** (Paris Open Data, format GBFS, mise à jour chaque minute).

**Équipe :** Ibrahima Ndaw · Saer Diene

## Architecture

```mermaid
flowchart LR
    src["🚲 API Vélib' Métropole<br/>GBFS · mise à jour ~1 min<br/>station_status · station_information"]

    subgraph azure["Azure · rg-velib-platform · francecentral"]
        direction LR

        subgraph ingest["Ingestion · Azure Data Factory"]
            adf["pl_ingest_velib<br/>trigger toutes les 15 min (5 min en démo)<br/>ForEach · Lookup · Copy · retry 3×"]
            check{"Au moins<br/>une station ?"}
            fail["❌ Fail<br/>INVALID_PAYLOAD"]
        end

        subgraph lake["ADLS Gen2 · stvelibmwzyy4"]
            bronze[("bronze<br/>JSON brut<br/>velib/feed/yyyy/MM/dd/HH/mm.json")]
            silver[("silver<br/>Delta · 1 ligne par<br/>station et instantané")]
            gold[("gold · Delta<br/>network_snapshot · zone_snapshot<br/>station_timeseries · station_latest")]
        end

        subgraph synapse["Azure Synapse Analytics"]
            spark["Spark pool sparkvelib<br/>nb_velib_processing<br/>+ transform.py"]
            sql["SQL serverless<br/>base velib · 4 vues"]
        end

        kv["🔐 Key Vault"]
        monitor["🔔 Azure Monitor<br/>alerte run en échec<br/>→ mail à l'équipe"]
    end

    fabric["🟩 Microsoft Fabric<br/>Lakehouse lh_velib<br/>raccourcis vers gold"]
    pbi["📊 Power BI<br/>Direct Lake<br/>actualisation auto"]
    tf["🛠️ Terraform · azurerm"]
    ci["✅ GitHub Actions<br/>lint · tests · terraform validate"]

    src -- "HTTP GET" --> adf
    adf --> check
    check -- "oui" --> bronze
    check -- "non" --> fail
    adf -. "si l'ingestion réussit :<br/>lance le notebook" .-> spark
    bronze -- "nouveaux instantanés" --> spark
    spark -- "1 · nettoyage, jointure,<br/>MERGE sans doublons" --> silver
    spark -- "2 · KPI, anomalies" --> gold
    gold --> sql
    gold -- "raccourcis OneLake" --> fabric
    fabric --> pbi

    adf -. "runs en échec" .-> monitor
    kv -. "identités managées" .- adf
    kv -. "identités managées" .- spark
    tf -. "déploie" .-> azure
    ci -. "vérifie" .-> tf
```

- **Ingestion :** ADF interroge l'API Vélib' toutes les 15 min (5 min pendant la démo), vérifie que la réponse contient des stations et écrit le JSON brut dans `bronze`. Il lance ensuite le notebook de traitement.
- **Traitement :** le notebook PySpark `nb_velib_processing` nettoie les nouveaux instantanés (`silver`, Delta, `MERGE` sans doublons) puis recalcule les KPI (`gold`). Le code vient de [`transform.py`](src/data_platform_project/transform.py), testé en local.
- **Exposition :** le rapport Power BI tourne dans Microsoft Fabric. Un Lakehouse lit les 4 tables `gold` par raccourcis OneLake (aucune copie), et le modèle sémantique est en mode Direct Lake. Des vues SQL serverless (base `velib`) exposent aussi `gold` pour un accès SQL ou Power BI Desktop. Voir [powerbi/](powerbi/).
- **Sécurité :** aucune clé ni mot de passe ; ADF et Synapse accèdent au Data Lake et au Key Vault par identité managée.
- **Supervision :** une alerte Azure Monitor envoie un mail à l'équipe dès qu'un run du pipeline échoue.
- **Infrastructure :** toutes les ressources Azure sont déployées par Terraform ([infra/](infra/)), vérifié à chaque push par la CI GitHub Actions.

## Organisation du repo

| Dossier | Contenu |
|---|---|
| `infra/` | Terraform (azurerm) |
| `factory/`, `linkedService/`, `dataset/`, `pipeline/`, `trigger/` | Ressources Azure Data Factory, commitées automatiquement par l'intégration Git d'ADF (root folder `/`) |
| `publish_config.json` | Configuration de publication ADF (branche `adf_publish`) |
| `synapse/` | Notebooks PySpark et scripts SQL serverless |
| `src/data_platform_project/` | Fonctions Python réutilisables |
| `tests/` | Tests unitaires pytest |
| `powerbi/` | Rapport Power BI (Fabric) : export PDF, captures, mesures DAX |
| `docs/` | Architecture, guide de déploiement, slides |
| `.github/workflows/` | CI : lint, tests, validation Terraform |

## Développement local

Prérequis : Python 3.13 et [uv](https://docs.astral.sh/uv/).

```bash
uv sync              # installer les dépendances
uv run pytest        # lancer les tests
uv run ruff check .  # lint
uv run black .       # formatage
```

La CI GitHub Actions ([ci.yml](.github/workflows/ci.yml)) lance les mêmes vérifications à chaque push et pull request, plus `terraform fmt -check` et `terraform validate` sur [infra/](infra/).

Les tests de `transform.py` lancent un Spark local : ils demandent **Java 17 ou plus** et prennent environ 30 s. Sous Windows, ils corrigent eux-mêmes `SPARK_HOME` et `JAVA_HOME` pour la session de test (chemin avec espaces, installation Spark globale).

## Déploiement

1. **Infrastructure :** `terraform apply` dans [infra/](infra/) (voir [infra/README.md](infra/README.md)).
2. **ADF :** l'intégration Git lit `main` (root folder `/`). Dans ADF Studio : *Validate*, *Debug*, puis *Publish* pour activer le déclencheur `tr_every_15min`.
3. **Code de traitement :** copier `transform.py` sur le lac, où le notebook le charge :
   ```bash
   az storage fs file upload -f synapse -s src/data_platform_project/transform.py \
     -p libs/transform.py --account-name stvelibmwzyy4 --auth-mode login --overwrite
   ```
4. **Notebook :** importer [synapse/notebooks/nb_velib_processing.ipynb](synapse/notebooks/nb_velib_processing.ipynb) dans Synapse (pool `sparkvelib`).
5. **Vues SQL :** dans Synapse Studio (pool *Built-in*), exécuter [01_create_database.sql](synapse/sql/01_create_database.sql) sur `master`, puis [02_create_gold_views.sql](synapse/sql/02_create_gold_views.sql).
6. **Power BI (Fabric) :** Lakehouse avec raccourcis vers `gold`, modèle sémantique en Direct Lake, rapport `rpt_velib` (voir [powerbi/README.md](powerbi/README.md)). Alternative avec Power BI Desktop : *Azure Synapse Analytics SQL*, serveur `synw-velib-mwzyy4-ondemand.sql.azuresynapse.net`, base `velib`, mode DirectQuery.

### Données produites

| Couche | Emplacement | Contenu |
|---|---|---|
| bronze | `bronze/velib/<flux>/yyyy/MM/dd/HH/mm.json` | JSON brut de l'API, un fichier par flux et par run |
| silver | `silver/velib/station_status` (Delta) | Une ligne par station et instantané, enrichie (nom, GPS, capacité, zone, états) |
| gold | `gold/velib/network_snapshot` | KPI du réseau par instantané |
| gold | `gold/velib/zone_snapshot` | KPI par arrondissement ou commune |
| gold | `gold/velib/station_timeseries` | Historique par station, moyenne glissante 1 h, anomalies |
| gold | `gold/velib/station_latest` | Dernier état de chaque station (carte) |

## Documentation projet

- [Cahier des charges](CAHIER_DES_CHARGES.md)
- [TODO](TODO.md)
