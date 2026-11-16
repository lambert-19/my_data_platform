# TODO – My Data Platform : Scale (5CLOU)

> **Deadline :** mercredi 18 novembre 2026, 23:59
> **Barème :** 28 pts + 2 pts bonus (Terraform)
> **Livrables :** zip du repo GitHub + démo live sur Azure (15 min + 5 min Q&A) + support type PowerPoint

---

## 📊 État au 16 novembre 2026 (soir) : ~65 %

| Partie | Points | État |
|---|---|---|
| Cadrage, source, structure | – | ✅ fait |
| Accès Azure d'Ibrahima | – | ✅ vérifié (portail + Azure CLI) |
| Terraform (bonus) | 2 | 🟡 infra Azure + alerte + rôle Synapse d'ADF en code ; reste l'`apply` de Saer et la partie Fabric |
| Qualité du code & repo | 2 | 🟢 CI GitHub Actions, PR #1 à #6, 30 tests, clone à neuf validé ; reste les captures |
| **Ingestion ADF** | **6** | ✅ pipeline publié : ingestion + validation + notebook Synapse, alerte mail ; latence de bout en bout ~3 à 5 min |
| **Traitement Synapse** | **6** | ✅ notebook bronze → silver → gold lancé par ADF à chaque run + vues SQL serverless |
| **Power BI** | **4** | 🔴 à faire |
| Slides, oral, Q&A | 10 | 🔴 à faire (ensemble) |

**Premiers résultats (16 nov, 18h19 UTC) :** 1 525 stations, 17 673 vélos (11 035 mécaniques, 6 638 électriques), 35 % d'occupation ; centre de Paris (1er–4e) à 70–74 %, Est et Nord (14e, 18e, 19e, 20e) sous 20 %.

**Priorités d'ici au rendu :**
1. **17 nov (matin) :** relancer le déclencheur, slides, captures
2. **17 nov (après-midi) :** dashboard Power BI (garder au moins une demi-journée) + vidéo de secours
3. **18 nov :** répétitions, zip, rendu avant 23:59

---

## 📅 Planning initial

| Semaine | Période | Objectif | Réalisé |
|---|---|---|---|
| S1 | 21 – 27 oct | Setup, choix de la source, base Terraform | ✅ |
| S2 | 28 oct – 3 nov | Ingestion ADF fonctionnelle de bout en bout | ✅ (rattrapé le 16 nov) |
| S3 | 4 – 10 nov | Traitement Synapse + dashboard Power BI | 🟡 Synapse fait le 16 nov, Power BI en cours |
| S4 | 11 – 18 nov | Finitions, documentation, slides, répétitions, rendu | 🔴 en cours |

---

## Phase 0 – Cadrage & setup ✅

- [x] Choisir la source de données → **Vélib' Métropole** (Paris Open Data, GBFS, mise à jour ~1 min)
- [x] Tester les appels (pas de clé API nécessaire) → client [`velib.py`](src/data_platform_project/velib.py) + données d'exemple dans `tests/data/`
- [x] Créer le repo GitHub (`lambert-19/my_data_platform`), travail en branches + pull requests, convention de commits (`feat:`, `fix:`, `docs:`…)
- [ ] Vérifier que `main` est protégée sur GitHub (Settings → Branches)
- [x] Mettre en place l'arborescence du repo :
  ```
  /infra     → Terraform
  /factory, /linkedService, /dataset, /pipeline, /trigger → ressources ADF (intégration Git, root folder /)
  /synapse   → notebooks, scripts SQL
  /src       → modules Python de transformation
  /tests     → tests unitaires
  /powerbi   → .pbix + captures
  /docs      → schéma d'architecture, guides
  README.md
  ```
- [x] Activer le GitHub Student Developer Pack → crédits Azure for Students (souscription de Saer), région `francecentral`
- [ ] Vérifier l'accès à Microsoft Fabric / Power BI Service (essai Fabric avec le compte SUPINFO) — nécessaire pour Power BI et le bonus Terraform
- [x] ~~Plan B local~~ → non nécessaire, l'accès Azure fonctionne
- [x] Dessiner le schéma d'architecture → Mermaid dans le [README](README.md)
- [x] Répartir les rôles → voir [docs/AVANCEMENT.md](docs/AVANCEMENT.md) (Saer : setup + infra ; Ibrahima : ADF, Synapse, Power BI)
- [x] Compléter la section 11 (rôles) du [cahier des charges](CAHIER_DES_CHARGES.md)
- [ ] Relire et valider le cahier des charges à deux

## Phase 1 – Infrastructure as Code avec Terraform (bonus 2 pts) 🟡

- [x] Backend distant pour le state (`rg-velib-tfstate`)
- [x] Resource Group (`rg-velib-platform`)
- [x] Storage Account ADLS Gen2 + containers `bronze`, `silver`, `gold`
- [x] Key Vault (secrets de connexion ; pas de clé pour Vélib')
- [x] Azure Data Factory avec identité managée
- [x] Synapse Workspace + Spark pool `sparkvelib` (auto-pause activé) + SQL serverless
- [x] Role assignments (Storage Blob Data Contributor, accès Key Vault pour ADF et Synapse, droits de l'équipe)
- [x] Budget avec alertes mail à 50, 80 et 100 %
- [x] Variables, outputs, `terraform.tfvars.example` — aucun secret commité
- [ ] Provider **Microsoft Fabric** (`microsoft/fabric`) recommandé par le sujet : workspace Fabric pour Power BI (`fabric_workspace`), rattaché à une capacité Fabric (essai ou SKU F)
- [ ] Combiner les deux providers : `azurerm` (Storage, Key Vault, ADF, Synapse) + `fabric` (workspace / éléments Power BI)
- [x] Alerte mail (`monitoring.tf`) et rôle Synapse d'ADF (`rbac.tf`) décrits en Terraform, avec des blocs `import` pour les ressources créées à la main
- [x] `budget.tf` : date de départ en variable (`plantimestamp()` cassait `terraform validate`)
- [ ] **Saer :** ajouter `alert_emails = ["ibrahima.ndaw@supinfo.com", "saer.diene@supinfo.com"]` dans `terraform.tfvars`, lancer `terraform apply`, puis supprimer `infra/imports.tf`
- [x] CI GitHub Actions : `terraform fmt -check` + `terraform validate` (pas de `plan` : pas d'identifiants Azure dans la CI)

## Phase 2 – Ingestion avec Azure Data Factory (6 pts) ✅

> Les ressources ADF sont commitées sur `main` (intégration Git) : [`pipeline/pl_ingest_velib.json`](pipeline/pl_ingest_velib.json), `dataset/`, `linkedService/`, `trigger/`.

- [x] Activer l'intégration Git d'ADF (repo `lambert-19/my_data_platform`, branche `main`, root folder `/`, publication sur `adf_publish`)
- [x] Linked service `ls_http_velib` : HTTP Vélib' (anonyme)
- [x] Linked service `ls_adls_velib` : ADLS Gen2 (identité managée)
- [x] Linked service `ls_keyvault_velib` : Key Vault (identité managée, publié, prêt pour de futurs secrets)
- [x] Datasets `ds_velib_feed` (HTTP JSON, paramètre `feed`) et `ds_bronze_json` (ADLS JSON, paramètres `folderPath` / `fileName`)
- [x] Copy activity (ForEach sur `station_status` et `station_information`) → JSON brut dans `bronze/velib/<flux>/yyyy/MM/dd/HH/mm.json` (testé : fichiers identiques à l'API)
- [x] Paramétrer le pipeline (paramètre `feeds`, chemin horodaté sur `TriggerTime`, 2 DIU)
- [x] Trigger `tr_every_15min` publié et actif depuis le 16 nov 19h00 UTC (runs toutes les 15 min en succès)
- [ ] Arrêter le trigger la nuit et le relancer le matin (*Manage* → *Triggers* → *Stop* / *Start* → **Publish**)
- [ ] Passer le trigger à 5 min pour la démo
- [x] Gestion des erreurs :
  - [x] Retry policy + timeout sur les activités (3 × 30 s, timeout 5 min)
  - [x] Validation de la réponse : `LookupFeed` + `IfFeedIsValid` (au moins une station), sinon `FailInvalidFeed` (`INVALID_PAYLOAD`)
  - [x] Chemin « on failure » : `FailIngestion` (`INGESTION_FAILED`, message d'erreur explicite)
  - [x] Alerte mail `alert-adf-failed-runs` (*Failed pipeline runs* > 0, vérifiée toutes les 5 min) → groupe `ag-velib-alerts` (Ibrahima + Saer). Créée en Azure CLI, pas encore dans Terraform
- [x] Activité `RunProcessingNotebook` après l'ingestion (linked service `ls_synapse_velib`, identité d'ADF *Synapse Administrator* sur le workspace)
- [x] Pipeline complet publié : runs automatiques de 21h30 et 21h45 UTC en succès (3 à 5 min, démarrage de Spark compris)
- [ ] Captures d'exécutions réussies (*Monitor*) et des fichiers dans `bronze` pour les slides
- [ ] (Optionnel) Event Hubs + Spark Structured Streaming pour un vrai temps réel

## Phase 3 – Traitement temps réel avec Synapse & Python (6 pts) ✅

> Notebook : [`synapse/notebooks/nb_velib_processing.ipynb`](synapse/notebooks/nb_velib_processing.ipynb) · vues : [`synapse/sql/`](synapse/sql/) (PR #5).

- [x] Lier le Data Lake au workspace Synapse (fait par Terraform) ; lire en `abfss://<container>@stvelibmwzyy4.dfs.core.windows.net/...`
- [x] Quota Spark OK : `sparkvelib` démarre et exécute le notebook
- [x] Logique réutilisable dans [`transform.py`](src/data_platform_project/transform.py) (bronze → silver → gold, anomalies, watermark) + 15 tests dans `tests/test_transform.py`
- [x] `transform.py` vérifié sur le pool (Spark 3.4) : chargé depuis `abfss://synapse@stvelibmwzyy4.dfs.core.windows.net/libs/transform.py` avec `sc.addPyFile` (un seul code source pour les tests et Synapse)
- [ ] Après chaque modification de `transform.py`, le recopier sur le lac (commande dans le [README](README.md#déploiement))
- [x] Fuseau horaire UTC et 8 partitions de shuffle fixés dans le notebook
- [x] **Bronze → silver** : parsing JSON, schéma explicite, typage, dédoublonnage (`station_id`, `ingested_at`), valeurs nulles, jointure `station_information`
- [x] **Silver → gold** : 4 tables (`network_snapshot`, `zone_snapshot`, `station_timeseries`, `station_latest`) : occupation, vides / pleines / hors service, moyenne glissante 1 h, anomalies
- [x] Écriture en Delta (silver partitionné par `snapshot_date`)
- [x] Traitement incrémental : watermark sur `ingested_at` + `MERGE` Delta (rejouable sans doublons)
- [x] Vues SQL serverless sur gold dans la base `velib` (testées : 2 instantanés lisibles)
- [x] Logs : lignes, instantanés, latence, durée (run manuel : 51 s)
- [x] Latence de bout en bout mesurée : ~3 à 5 min entre l'appel API et gold (cible ≤ 20 min, ENF1)

## Phase 4 – Visualisation avec Power BI (4 pts) 🔴

- [ ] Vérifier que Power BI Desktop est installé
- [ ] Connexion aux vues Synapse serverless (`synw-velib-mwzyy4-ondemand.sql.azuresynapse.net`) en **DirectQuery**
- [ ] Actualisation automatique de page (ou dataset streaming / push)
- [ ] Visuels : cartes KPI, courbe temporelle, carte des stations, filtres (zone / station / type de vélo), mise en évidence des anomalies
- [ ] Zone « insights clés » mettant en avant les conclusions
- [ ] Publication sur le Power BI Service (identifiants, actualisation planifiée)
- [ ] `.pbix` + captures d'écran dans `/powerbi`

## Phase 5 – Qualité du code & repo (2 pts) 🟡

- [ ] README : ~~résumé~~ ✅, ~~schéma d'architecture~~ ✅, ~~stack~~ ✅, ~~procédure de déploiement~~ ✅, captures, répartition des rôles
- [x] Formatage / lint Python configurés (`black`, `ruff`, `pytest` via uv)
- [x] `.gitignore` : `.tfstate`, `.terraform/`, `.env`, secrets
- [x] Branches + pull requests (PR #1 à #6)
- [x] CI GitHub Actions ([`ci.yml`](.github/workflows/ci.yml)) à chaque push et PR : `ruff`, `black`, `pytest`, `terraform fmt` + `validate`
- [ ] Vérifier que la CI est verte dans l'onglet *Actions* de GitHub
- [ ] Commits réguliers et explicites de **chaque** membre jusqu'au rendu
- [x] Test final : clone à neuf → `uv sync --locked` → lint → 30/30 tests (16 nov)
- [x] Dossier `adf/` vide supprimé

## Phase 6 – Présentation & démo 🔴

- [ ] Slides (~10–12) :
  1. Titre & équipe
  2. **Introduction & objectifs** (2 pts)
  3. Architecture
  4. Source : Vélib' Métropole & justification
  5. Ingestion
  6. Traitement
  7. Dashboard
  8. IaC
  9. Difficultés & choix techniques
  10. Coûts
  11. Perspectives
- [ ] Script de démo : lancer le pipeline → fichier dans bronze → traitement → dashboard mis à jour
- [ ] Plan B : vidéo de la démo + captures (en cas de panne Azure / réseau)
- [ ] Jour J : Spark pool démarré à l'avance, triggers actifs
- [ ] 2 répétitions chronométrées minimum, tout le monde parle (aisance orale, 2 pts)
- [ ] Préparation Q&A (6 pts) — chacun doit savoir répondre :
  - [ ] Pourquoi ADF plutôt que Logic Apps / Functions ? ADF est-il vraiment temps réel ? Quelle latence ?
  - [ ] Spark pool vs SQL pool dédié ? Serverless vs dédié ? Coûts ?
  - [ ] DirectQuery vs Import ? Comment le dashboard se rafraîchit-il ?
  - [ ] Gestion des secrets (Key Vault, identité managée) ?
  - [ ] Que se passe-t-il si l'API tombe ou renvoie des données invalides ?
  - [ ] Comment passer à l'échelle ×100 ?
  - [ ] Rôle du state Terraform ? Déployer un 2e environnement ?
  - [ ] Coût total et maîtrise des dépenses ?

## Phase 7 – Plan B local ⏸️ non nécessaire

> L'accès Azure fonctionne. À n'utiliser qu'en cas de panne bloquante, la grille note explicitement ADF / Synapse / Power BI.

- [ ] Ingestion : Apache Airflow via Docker, DAG planifié (`schedule`, retries) → CSV / SQLite
  - utiliser `from airflow.operators.python import PythonOperator` (l'import `python_operator` du sujet est obsolète)
- [ ] Traitement : scripts Pandas (nettoyage, filtres, agrégats) → CSV nettoyé
- [ ] Visualisation : Jupyter (matplotlib / plotly) ou Tableau Public
- [ ] Garder la même architecture bronze / silver / gold pour pouvoir migrer vers Azure

## Rendu (avant le 18 nov, 23:59)

- [ ] Zip du repo (docs, scripts, `.pbix`) — vérifier l'absence de secrets
- [ ] Slides ajoutées au repo et au rendu
- [ ] Après la notation : `terraform destroy` pour préserver les crédits
