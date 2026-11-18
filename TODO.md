# TODO – My Data Platform : Scale (5CLOU)

> **Deadline :** mercredi 18 novembre 2026, 23:59
> **Barème :** 28 pts + 2 pts bonus (Terraform)
> **Livrables :** zip du repo GitHub + démo live sur Azure (15 min + 5 min Q&A) + support type PowerPoint

---

## 📊 État au 18 novembre 2026 (jour du rendu) : ~90 %

| Partie | Points | État |
|---|---|---|
| Cadrage, source, structure | – | ✅ fait |
| Terraform (bonus) | 2 | 🟢 toute l'infra Azure en code, `apply` du 17 nov sans drift ; Fabric créé à la main (limite documentée) |
| Qualité du code & repo | 2 | ✅ CI GitHub Actions, PR #1 à #11, 30 tests, clone à neuf validé, captures |
| **Ingestion ADF** | **6** | ✅ pipeline publié : ingestion + validation + notebook Synapse, alerte mail ; latence de bout en bout ~3 à 5 min |
| **Traitement Synapse** | **6** | ✅ notebook bronze → silver → gold lancé par ADF à chaque run + 8 vues SQL serverless |
| **Power BI** | **4** | ✅ rapport `rpt_velib` dans Fabric (Direct Lake, 2 pages, actualisation auto) |
| Slides, oral, Q&A | 10 | 🟡 slides faites (17) ; reste la répétition, la vidéo de secours et la révision du Q&A |

**Résultats :** 53 instantanés dans bronze au 18 nov midi. Le centre de Paris (1er–4e) dépasse 60 % d'occupation, le 14e et le 20e sont autour de 20 % ; il reste 35 % de vélos électriques à Paris contre 52 % en banlieue.

**Reste aujourd'hui :**
1. Répétition chronométrée (15 min) + vidéo de secours de la démo
2. Avant la démo : déclencheur à 5 min, *Started*, **Publish** ; un run 10 min avant pour chauffer Spark
3. Zip du repo, rendu avant 23:59

---

## 📅 Planning initial

| Semaine | Période | Objectif | Réalisé |
|---|---|---|---|
| S1 | 21 – 27 oct | Setup, choix de la source, base Terraform | ✅ |
| S2 | 28 oct – 3 nov | Ingestion ADF fonctionnelle de bout en bout | ✅ (rattrapé le 16 nov) |
| S3 | 4 – 10 nov | Traitement Synapse + dashboard Power BI | ✅ (Synapse le 16 nov, Power BI le 17 nov) |
| S4 | 11 – 18 nov | Finitions, documentation, slides, répétitions, rendu | 🟡 slides et docs faites, répétition et rendu le 18 |

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
  /powerbi   → rapport Fabric : export PDF, captures, mesures DAX
  /docs      → slides, captures, suivi d'avancement
  README.md
  ```
- [x] Activer le GitHub Student Developer Pack → crédits Azure for Students (souscription de Saer), région `francecentral`
- [x] Accès à Microsoft Fabric : capacité d'essai, workspace `velib-platform`
- [x] ~~Plan B local~~ → non nécessaire, l'accès Azure fonctionne
- [x] Dessiner le schéma d'architecture → Mermaid dans le [README](README.md)
- [x] Répartir les rôles → voir [docs/AVANCEMENT.md](docs/AVANCEMENT.md) (Saer : setup + infra ; Ibrahima : ADF, Synapse, Power BI)
- [x] Compléter la section 11 (rôles) du [cahier des charges](CAHIER_DES_CHARGES.md)
- [ ] Relire et valider le cahier des charges à deux

## Phase 1 – Infrastructure as Code avec Terraform (bonus 2 pts) 🟢

- [x] Backend distant pour le state (`rg-velib-tfstate`)
- [x] Resource Group (`rg-velib-platform`)
- [x] Storage Account ADLS Gen2 + containers `bronze`, `silver`, `gold`
- [x] Key Vault (secrets de connexion ; pas de clé pour Vélib')
- [x] Azure Data Factory avec identité managée
- [x] Synapse Workspace + Spark pool `sparkvelib` (auto-pause activé) + SQL serverless
- [x] Role assignments (Storage Blob Data Contributor, accès Key Vault pour ADF et Synapse, droits de l'équipe)
- [x] Budget avec alertes mail à 50, 80 et 100 %
- [x] Variables, outputs, `terraform.tfvars.example` — aucun secret commité
- [ ] Provider **Microsoft Fabric** (`microsoft/fabric`) : workspace, Lakehouse et rapport créés dans l'interface Fabric, non faits en Terraform faute de temps → présenté comme piste d'amélioration (slide 15)
- [x] Alerte mail (`monitoring.tf`) et rôle Synapse d'ADF (`rbac.tf`) décrits en Terraform, avec des blocs `import` pour les ressources créées à la main
- [x] `budget.tf` : date de départ en variable (`plantimestamp()` cassait `terraform validate`)
- [x] `terraform apply` du 17 nov (Saer) : alerte et rôle Synapse d'ADF adoptés dans le state (tags du projet appliqués), drift corrigé avec `ignore_changes` (lien Git d'ADF, login SQL de Synapse) — PR #8
- [ ] Supprimer `infra/imports.tf`, devenu inutile
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
- [x] Trigger `tr_every_15min` publié, arrêté la nuit et relancé en journée (53 instantanés au 18 nov midi)
- [ ] **Avant la démo :** passer le trigger à 5 min, *Started*, puis **Publish** (actuellement *Stopped* sur Azure)
- [x] Gestion des erreurs :
  - [x] Retry policy + timeout sur les activités (3 × 30 s, timeout 5 min)
  - [x] Validation de la réponse : `LookupFeed` + `IfFeedIsValid` (au moins une station), sinon `FailInvalidFeed` (`INVALID_PAYLOAD`)
  - [x] Chemin « on failure » : `FailIngestion` (`INGESTION_FAILED`, message d'erreur explicite)
  - [x] Alerte mail `alert-adf-failed-runs` (*Failed pipeline runs* > 0, vérifiée toutes les 5 min) → groupe `ag-velib-alerts` (Ibrahima + Saer), gérée par Terraform (`monitoring.tf`)
- [x] Activité `RunProcessingNotebook` après l'ingestion (linked service `ls_synapse_velib`, identité d'ADF *Synapse Administrator* sur le workspace)
- [x] Pipeline complet publié : runs automatiques de 21h30 et 21h45 UTC en succès (3 à 5 min, démarrage de Spark compris)
- [x] Captures du pipeline et des runs ([docs/captures/](docs/captures/))
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
- [x] 4 vues d'analyse : `zone_flow`, `zone_indicators`, `paris_vs_suburbs`, `station_issues` (PR #9)
- [x] Logs : lignes, instantanés, latence, durée (run manuel : 51 s)
- [x] Latence de bout en bout mesurée : ~3 à 5 min entre l'appel API et gold (cible ≤ 20 min, ENF1)

## Phase 4 – Visualisation avec Power BI (4 pts) ✅

> Détail : [`powerbi/README.md`](powerbi/README.md) (PR #10).

- [x] Workspace Fabric `velib-platform` (capacité d'essai), construit entièrement dans le navigateur
- [x] Lakehouse `lh_velib` : 4 raccourcis OneLake vers `gold/velib/*` (aucune copie, accès Entra ID)
- [x] Modèle sémantique `sm_velib` en **Direct Lake** (remplace le DirectQuery prévu : lit le Delta directement, toujours à jour)
- [x] Mesures DAX « dernier instantané » (KPI) et indicateurs par zone (occupation, tension, part d'électriques)
- [x] Actualisation automatique des pages
- [x] Page « Réseau en direct » : KPI, évolution des vélos disponibles, carte Azure Maps des stations colorée par anomalie
- [x] Page « Analyses » : occupation par arrondissement, Paris contre banlieue, tension par zone, top 10 des stations à problème
- [x] Export PDF + captures dans `/powerbi`
- [x] Qualité des données documentée : instantanés sans code station → zone vide, filtrée dans les visuels

## Phase 5 – Qualité du code & repo (2 pts) ✅

- [x] README : résumé, schéma d'architecture (Mermaid à jour avec Fabric), procédure de déploiement, données produites, liens vers les docs
- [x] Formatage / lint Python configurés (`black`, `ruff`, `pytest` via uv)
- [x] `.gitignore` : `.tfstate`, `.terraform/`, `.env`, secrets
- [x] Branches + pull requests (PR #1 à #11)
- [x] CI GitHub Actions ([`ci.yml`](.github/workflows/ci.yml)) à chaque push et PR : `ruff`, `black`, `pytest`, `terraform fmt` + `validate`
- [ ] Vérifier que la CI est verte dans l'onglet *Actions* de GitHub
- [x] Commits réguliers et explicites des deux membres
- [x] Test final : clone à neuf → `uv sync --locked` → lint → 30/30 tests (16 nov)
- [x] Dossier `adf/` vide supprimé

## Phase 6 – Présentation & démo 🟡

- [x] Slides ([docs/slides_velib.pptx](docs/slides_velib.pptx), 17 slides) : titre, source, architecture, ingestion, couches du lac, traitement, résultats, analyse par zone, dashboard, Fabric, Terraform, sécurité et supervision, coûts, qualité, limites, démo
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

- [ ] Zip du repo (docs, scripts, rapport PDF) — vérifier l'absence de secrets
- [x] Slides ajoutées au repo ([docs/slides_velib.pptx](docs/slides_velib.pptx))
- [ ] Après la notation : `terraform destroy`, supprimer `rg-velib-tfstate` et le workspace Fabric
