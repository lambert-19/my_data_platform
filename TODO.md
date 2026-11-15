# TODO – My Data Platform : Scale (5CLOU)

> **Deadline :** mercredi 18 novembre 2026, 23:59
> **Barème :** 28 pts + 2 pts bonus (Terraform)
> **Livrables :** zip du repo GitHub + démo live sur Azure (15 min + 5 min Q&A) + support type PowerPoint

---

## 📊 État au 15 novembre 2026 : ~25 %

| Partie | Points | État |
|---|---|---|
| Cadrage, source, structure | – | ✅ fait |
| Terraform (bonus) | 2 | 🟡 infra Azure déployée, reste la partie Fabric / Power BI |
| Qualité du code & repo | 2 | 🟡 en bonne voie |
| **Ingestion ADF** | **6** | 🔴 à faire (Ibrahima) |
| **Traitement Synapse** | **6** | 🔴 à faire (Ibrahima) |
| **Power BI** | **4** | 🔴 à faire (Ibrahima) |
| Slides, oral, Q&A | 10 | 🔴 à faire (ensemble) |

**Priorités d'ici au rendu :**
1. **15 nov :** pipeline ADF → données dans `bronze` + `transform.py` en local sur `tests/data/`
2. **16 nov :** notebooks Synapse → `silver` / `gold` + vues SQL serverless
3. **17 nov :** dashboard Power BI + slides + vidéo de secours
4. **18 nov :** répétitions, zip, rendu avant 23:59

---

## 📅 Planning initial

| Semaine | Période | Objectif | Réalisé |
|---|---|---|---|
| S1 | 21 – 27 oct | Setup, choix de la source, base Terraform | ✅ |
| S2 | 28 oct – 3 nov | Ingestion ADF fonctionnelle de bout en bout | 🟡 infra seulement |
| S3 | 4 – 10 nov | Traitement Synapse + dashboard Power BI | 🔴 en retard |
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
  /adf       → pipelines ADF (JSON, intégration Git)
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
- [ ] Valider le cahier des charges ([CAHIER_DES_CHARGES.md](CAHIER_DES_CHARGES.md)) en équipe et compléter la section 11 (rôles)

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
- [ ] (Optionnel) GitHub Actions : `terraform fmt` / `validate` / `plan`

## Phase 2 – Ingestion avec Azure Data Factory (6 pts) 🔴

> Guide pas à pas : [docs/AVANCEMENT.md](docs/AVANCEMENT.md), étape 3. Branche `feat/adf-ingestion`.

- [ ] Activer l'intégration Git d'ADF **en premier** (root folder `/adf`), pipelines versionnés dans le repo
- [ ] Linked services : HTTP Vélib' (anonyme), ADLS Gen2 (identité managée), Key Vault
- [ ] Copy activity (ForEach sur `station_status` et `station_information`) → JSON brut dans `bronze/velib/<flux>/yyyy/MM/dd/HH/mm.json`
- [ ] Paramétrer le pipeline (liste des flux, chemin horodaté)
- [ ] Trigger planifié toutes les 5 min (Vélib' change chaque minute ; compromis fraîcheur / coût, à justifier à l'oral)
- [ ] Gestion des erreurs :
  - [ ] Retry policy + timeout sur les activités (3 × 30 s, timeout 5 min)
  - [ ] Chemin « on failure » (log d'erreur, alerte mail / Logic App)
  - [ ] Validation de la réponse (vide / invalide) via If Condition ou Validation
- [ ] Déclencher le notebook Synapse après l'ingestion (donner un rôle Synapse à l'identité d'ADF)
- [ ] Configurer les alertes de monitoring + captures d'exécutions réussies
- [ ] (Optionnel) Event Hubs + Spark Structured Streaming pour un vrai temps réel

## Phase 3 – Traitement temps réel avec Synapse & Python (6 pts) 🔴

> Guide pas à pas : [docs/AVANCEMENT.md](docs/AVANCEMENT.md), étape 4. Branche `feat/synapse-processing`.

- [x] Lier le Data Lake au workspace Synapse (fait par Terraform) ; lire en `abfss://<container>@stvelibmwzyy4.dfs.core.windows.net/...`
- [ ] Tester le quota Spark : notebook `print("ok")` sur `sparkvelib`
- [ ] Aligner les versions locales sur le Spark pool (Spark 3.4 / Python 3.10) : le projet est aujourd'hui en Python 3.13 et `pyspark>=4.2`, du code qui marche en local peut échouer sur Synapse
- [ ] Logique réutilisable dans `src/data_platform_project/transform.py` (fonctions documentées) + `tests/test_transform.py`
- [ ] Notebook PySpark **bronze → silver** : parsing JSON, schéma, typage, dédoublonnage, valeurs nulles, fuseaux horaires, jointure `station_information`
- [ ] Notebook **silver → gold** : KPI (taux d'occupation, stations vides / pleines / hors service, moyennes glissantes, anomalies)
- [ ] Écriture en Parquet / Delta partitionné par date
- [ ] Traitement incrémental (watermark ou Structured Streaming avec checkpoints)
- [ ] Vues SQL serverless sur la couche gold pour Power BI
- [ ] Logs : lignes en entrée / sortie, durée de traitement, latence de bout en bout

## Phase 4 – Visualisation avec Power BI (4 pts) 🔴

- [ ] Vérifier que Power BI Desktop est installé
- [ ] Connexion aux vues Synapse serverless (`synw-velib-mwzyy4-ondemand.sql.azuresynapse.net`) en **DirectQuery**
- [ ] Actualisation automatique de page (ou dataset streaming / push)
- [ ] Visuels : cartes KPI, courbe temporelle, carte des stations, filtres (zone / station / type de vélo), mise en évidence des anomalies
- [ ] Zone « insights clés » mettant en avant les conclusions
- [ ] Publication sur le Power BI Service (identifiants, actualisation planifiée)
- [ ] `.pbix` + captures d'écran dans `/powerbi`

## Phase 5 – Qualité du code & repo (2 pts) 🟡

- [ ] README : ~~résumé~~ ✅, ~~schéma d'architecture~~ ✅, ~~stack~~ ✅, procédure de déploiement, captures, répartition des rôles
- [x] Formatage / lint Python configurés (`black`, `ruff`, `pytest` via uv)
- [x] `.gitignore` : `.tfstate`, `.terraform/`, `.env`, secrets
- [x] Branches + pull requests (PR #1 à #4)
- [ ] Commits réguliers et explicites de **chaque** membre jusqu'au rendu
- [ ] Test final : cloner le repo à neuf et suivre le README

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
