# TODO – My Data Platform : Scale (5CLOU)

> **Deadline :** mercredi 18 novembre 2026, 23:59
> **Barème :** 28 pts + 2 pts bonus (Terraform)
> **Livrables :** zip du repo GitHub + démo live sur Azure (15 min + 5 min Q&A) + support type PowerPoint

---

## 📅 Planning

| Semaine | Période | Objectif |
|---|---|---|
| S1 | 21 – 27 oct | Setup, choix de la source, base Terraform |
| S2 | 28 oct – 3 nov | Ingestion ADF fonctionnelle de bout en bout |
| S3 | 4 – 10 nov | Traitement Synapse + dashboard Power BI |
| S4 | 11 – 18 nov | Finitions, documentation, slides, répétitions, rendu |

---

## Phase 0 – Cadrage & setup (S1)

- [ ] Choisir la source de données (mise à jour fréquente pour simuler le temps réel). Pistes du sujet : Paris Open Data, Alpha Vantage / Yahoo Finance, OpenWeatherMap
- [ ] Obtenir la clé API, tester les appels (Postman / curl), noter les limites de requêtes
- [ ] Créer le repo GitHub, protéger `main`, définir la convention de commits (`feat:`, `fix:`, `docs:`…)
- [ ] Mettre en place l'arborescence du repo :
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
- [ ] Activer le GitHub Student Developer Pack → crédits Azure for Students, et vérifier la région disponible
- [ ] Vérifier l'accès à Microsoft Fabric / Power BI Service (essai Fabric avec le compte école) — nécessaire pour Power BI et le bonus Terraform
- [ ] Si les crédits ou l'accès sont bloqués : basculer sur le plan B local (voir Phase 7) **dès la S1**, sans attendre
- [ ] Dessiner le schéma d'architecture : Source → ADF → ADLS Gen2 (bronze/silver/gold) → Synapse → Power BI
- [ ] Répartir les rôles : ingestion / traitement / dashboard / IaC & docs
- [ ] Valider le cahier des charges ([CAHIER_DES_CHARGES.md](CAHIER_DES_CHARGES.md)) en équipe

## Phase 1 – Infrastructure as Code avec Terraform (bonus 2 pts, S1–S2)

- [ ] Backend distant pour le state (Storage Account + container)
- [ ] Resource Group
- [ ] Storage Account ADLS Gen2 + containers `bronze`, `silver`, `gold`
- [ ] Key Vault (clé API, secrets de connexion)
- [ ] Azure Data Factory avec identité managée
- [ ] Synapse Workspace + Spark pool (auto-pause activé) + SQL serverless
- [ ] Role assignments (Storage Blob Data Contributor, accès Key Vault pour ADF et Synapse)
- [ ] Provider **Microsoft Fabric** (`microsoft/fabric`) recommandé par le sujet : workspace Fabric pour Power BI (`fabric_workspace`), rattaché à une capacité Fabric (essai ou SKU F)
- [ ] Combiner les deux providers : `azurerm` (Storage, Key Vault, ADF, Synapse) + `fabric` (workspace / éléments Power BI)
- [ ] Variables, outputs, `terraform.tfvars.example` — aucun secret commité
- [ ] (Optionnel) GitHub Actions : `terraform fmt` / `validate` / `plan`

## Phase 2 – Ingestion avec Azure Data Factory (6 pts, S2)

- [ ] Linked services : source REST/HTTP, ADLS Gen2, Key Vault
- [ ] Copy activity → JSON brut dans `bronze/<source>/yyyy/MM/dd/HH/mm.json`
- [ ] Paramétrer le pipeline (endpoint, chemin horodaté, liste de villes/actifs…)
- [ ] Trigger planifié (Schedule ou Tumbling Window) — le sujet cite « chaque minute ou chaque heure » ; viser 1 à 15 min selon la source et justifier l'intervalle
- [ ] Gestion des erreurs :
  - [ ] Retry policy + timeout sur les activités
  - [ ] Chemin « on failure » (log d'erreur, alerte mail / Logic App)
  - [ ] Validation de la réponse (vide / invalide) via If Condition ou Validation
- [ ] Déclencher le notebook Synapse après l'ingestion
- [ ] Activer l'intégration Git d'ADF (pipelines versionnés dans le repo)
- [ ] Configurer les alertes de monitoring + captures d'exécutions réussies
- [ ] (Optionnel) Event Hubs + Spark Structured Streaming pour un vrai temps réel

## Phase 3 – Traitement temps réel avec Synapse & Python (6 pts, S2–S3)

- [ ] Lier le Data Lake au workspace Synapse ; lire en `abfss://<container>@<compte>.dfs.core.windows.net/...` (ADLS Gen2) plutôt qu'en `wasbs://` comme dans l'exemple du sujet
- [ ] Notebook PySpark **bronze → silver** : parsing JSON, schéma, typage, dédoublonnage, valeurs nulles, fuseaux horaires
- [ ] Notebook **silver → gold** : agrégations et KPI (moyennes glissantes, min/max, tendances, anomalies)
- [ ] Écriture en Parquet / Delta partitionné par date
- [ ] Traitement incrémental (watermark ou Structured Streaming avec checkpoints)
- [ ] Vues SQL serverless sur la couche gold pour Power BI
- [ ] Logique réutilisable dans `/src` (fonctions documentées) + tests `pytest`
- [ ] Logs : lignes en entrée / sortie, durée de traitement, latence de bout en bout

## Phase 4 – Visualisation avec Power BI (4 pts, S3)

- [ ] Connexion aux vues Synapse serverless en **DirectQuery**
- [ ] Actualisation automatique de page (ou dataset streaming / push)
- [ ] Visuels : cartes KPI, courbe temporelle, carte ou répartition, filtres (date / lieu / catégorie), mise en évidence des anomalies
- [ ] Zone « insights clés » mettant en avant les conclusions
- [ ] Publication sur le Power BI Service (identifiants, actualisation planifiée)
- [ ] `.pbix` + captures d'écran dans `/powerbi`

## Phase 5 – Qualité du code & repo (2 pts, en continu)

- [ ] README : résumé, schéma d'architecture, stack, procédure de déploiement, captures, répartition des rôles
- [ ] Formatage / lint Python (`black`, `ruff`)
- [ ] `.gitignore` : `.tfstate`, `.terraform/`, `.env`, secrets
- [ ] Commits réguliers et explicites de **chaque** membre, branches + pull requests
- [ ] Test final : cloner le repo à neuf et suivre le README

## Phase 6 – Présentation & démo (S4)

- [ ] Slides (~10–12) :
  1. Titre & équipe
  2. **Introduction & objectifs** (2 pts)
  3. Architecture
  4. Source de données & justification
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

## Phase 7 – Plan B local (uniquement si Azure est inaccessible)

> Le sujet l'autorise, mais la grille note explicitement ADF / Synapse / Power BI : n'y recourir qu'en dernier ressort.

- [ ] Ingestion : Apache Airflow via Docker, DAG planifié (`schedule`, retries) → CSV / SQLite
  - utiliser `from airflow.operators.python import PythonOperator` (l'import `python_operator` du sujet est obsolète)
- [ ] Traitement : scripts Pandas (nettoyage, filtres, agrégats) → CSV nettoyé
- [ ] Visualisation : Jupyter (matplotlib / plotly) ou Tableau Public
- [ ] Garder la même architecture bronze / silver / gold pour pouvoir migrer vers Azure

## Rendu (avant le 18 nov, 23:59)

- [ ] Zip du repo (docs, scripts, `.pbix`) — vérifier l'absence de secrets
- [ ] Slides ajoutées au repo et au rendu
- [ ] Après la notation : `terraform destroy` pour préserver les crédits
