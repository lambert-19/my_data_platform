# Cahier des charges – My Data Platform : Scale

| | |
|---|---|
| **Module** | 5CLOU |
| **Période** | 19 octobre – 18 novembre 2026 |
| **Rendu** | 18 novembre 2026, 23:59 |
| **Équipe** | Ibrahima Ndaw -Saer Diene |
| **Version** | 1.0 – 21/10/2026 |

---

## 1. Contexte

Les organisations s'appuient de plus en plus sur des plateformes de données pour collecter, gérer et analyser leurs données en temps réel. Une plateforme de données réunit des outils d'ingestion, de traitement, de stockage et de visualisation pour permettre des décisions rapides et fondées sur les données.

Dans le cadre du module 5CLOU (« Building a unified data platform for real-time event analysis »), l'équipe doit concevoir et déployer une plateforme de données sur Microsoft Azure / Microsoft Fabric capable d'ingérer, de traiter et de visualiser des données en quasi temps réel, à partir d'une source de données ouverte : la disponibilité des stations **Vélib' Métropole** à Paris. Python est utilisé pour les transformations, le traitement et l'automatisation.

Le projet est évalué lors d'une démonstration live de 15 minutes suivie de 5 minutes de questions. Les crédits Azure sont obtenus via le GitHub Student Developer Pack (Azure for Students).

## 2. Objectifs

1. **Ingérer** automatiquement des données depuis une source externe à intervalle régulier.
2. **Traiter** ces données en Python (PySpark) pour produire des indicateurs exploitables.
3. **Visualiser** les résultats dans un dashboard Power BI interactif qui se met à jour automatiquement.
4. **Automatiser** le déploiement de l'infrastructure avec Terraform (bonus).
5. **Documenter** et versionner l'ensemble du projet dans un repo GitHub structuré.

## 3. Périmètre

### Inclus
- Pipeline d'ingestion Azure Data Factory planifié avec gestion des erreurs
- Stockage en Data Lake (ADLS Gen2) selon l'architecture médaillon (bronze / silver / gold)
- Traitement des données dans Azure Synapse Analytics (notebooks PySpark, SQL serverless)
- Dashboard Power BI publié sur le Power BI Service
- Infrastructure as Code avec Terraform
- Documentation technique et support de présentation

### Exclus
- Haute disponibilité multi-régions
- Gestion fine des utilisateurs finaux / sécurité au niveau ligne (RLS)
- Environnement de production (seul un environnement de dev / démo est déployé)

## 4. Source de données

| Critère | Valeur |
|---|---|
| Source retenue | **Vélib' Métropole** (Paris Open Data), format standard GBFS |
| URL de base | `https://velib-metropole-opendata.smovengo.cloud/opendata/Velib_Metropole` |
| Type d'accès | API HTTP publique (JSON) |
| Authentification | Aucune (pas de clé API) |
| Flux utilisés | `station_status.json` (vélos et bornes disponibles, ~1 min) · `station_information.json` (nom, lat/lon, capacité, quasi statique) |
| Volume | ~1 520 stations, jointes sur `station_id` |
| Fréquence de mise à jour de la source | Environ chaque minute |
| Limite de requêtes | Non documentée : usage raisonnable, 2 appels toutes les 5 min |
| Justification du choix | Données publiques, sans clé, mises à jour chaque minute, géolocalisées, avec des anomalies naturelles (stations vides, pleines ou hors service) qui rendent la démonstration temps réel parlante |

Le client Python de la source est dans [`src/data_platform_project/velib.py`](src/data_platform_project/velib.py) (téléchargement avec retry, validation des réponses, chemin bronze).

## 5. Architecture cible

```
┌──────────────┐    ┌───────────────────┐    ┌─────────────────────────────┐
│  API Vélib'  │───▶│ Azure Data Factory│───▶│ ADLS Gen2                   │
└──────────────┘    │ (trigger planifié)│    │  bronze → silver → gold     │
                    └─────────┬─────────┘    └──────────────┬──────────────┘
                              │ déclenche                    │
                              ▼                              ▼
                    ┌───────────────────────────────────────────────┐
                    │ Azure Synapse Analytics                       │
                    │  • Spark pool (PySpark) : nettoyage, KPI      │
                    │  • SQL serverless : vues sur la couche gold   │
                    └───────────────────────┬───────────────────────┘
                                            │ DirectQuery
                                            ▼
                                  ┌───────────────────┐
                                  │     Power BI      │
                                  │ (auto-refresh)    │
                                  └───────────────────┘

Transverse : Key Vault (secrets) · Identités managées · Terraform (IaC) · GitHub
```

### Services Azure utilisés

| Service | Rôle |
|---|---|
| Resource Group | Regroupe toutes les ressources du projet |
| ADLS Gen2 | Stockage des données brutes et transformées |
| Azure Key Vault | Stockage sécurisé des secrets (l'API Vélib' n'a pas de clé, prévu pour d'autres sources) |
| Azure Data Factory | Orchestration et ingestion planifiée |
| Azure Synapse Analytics | Traitement PySpark et exposition SQL |
| Power BI (Microsoft Fabric) | Visualisation et restitution, dans un workspace Fabric |
| Terraform (`azurerm` + `microsoft/fabric`) | Déploiement automatisé de l'infrastructure |

## 6. Exigences fonctionnelles

### EF1 – Ingestion (ADF)
- EF1.1 Le pipeline (activité Copy Data) interroge les deux flux Vélib' toutes les 5 min. La source change chaque minute, mais 5 min est un bon compromis entre fraîcheur et coût, et reste sous la latence cible de 20 min (ENF1).
- EF1.2 Les réponses brutes sont stockées sans modification dans `bronze/`, partitionnées par date et heure.
- EF1.3 Le pipeline est paramétré (endpoint, chemin de sortie, entités interrogées).
- EF1.4 En cas d'erreur : nouvelles tentatives automatiques, journalisation et alerte.
- EF1.5 Les réponses vides ou invalides sont détectées et ne sont pas propagées.
- EF1.6 Une ingestion réussie déclenche le traitement Synapse.

### EF2 – Traitement (Synapse / Python)
- EF2.1 **Bronze → silver :** parsing, typage, dédoublonnage, gestion des valeurs manquantes, normalisation des dates.
- EF2.2 **Silver → gold :** calcul des indicateurs : taux d'occupation (vélos / capacité) par station et global, part mécanique / électrique, nombre de stations vides, pleines et hors service, moyennes glissantes, répartition par zone, détection d'anomalies (station vide ou pleine depuis longtemps, chute brutale).
- EF2.3 Traitement incrémental : seules les nouvelles données sont traitées.
- EF2.4 Stockage au format Parquet / Delta partitionné.
- EF2.5 Exposition de la couche gold via des vues SQL serverless.

### EF3 – Visualisation (Power BI)
- EF3.1 Connexion à Synapse en DirectQuery.
- EF3.2 Actualisation automatique des pages pendant la démo.
- EF3.3 Le dashboard contient au minimum : cartes KPI, évolution temporelle de la disponibilité, carte des stations, filtres interactifs (zone, station, type de vélo), mise en évidence des stations en anomalie.
- EF3.4 Les insights clés sont explicitement mis en avant.

### EF4 – Infrastructure as Code (bonus)
- EF4.1 L'ensemble des ressources Azure (Storage, Key Vault, Data Factory, Synapse et Spark pool) est déployé via `terraform apply` avec le provider `azurerm`.
- EF4.2 Le state Terraform est stocké à distance.
- EF4.3 Le code est paramétré (variables, outputs) et ne contient aucun secret.
- EF4.4 La partie Power BI est déployée avec le provider Microsoft Fabric (`microsoft/fabric`) : workspace Fabric rattaché à une capacité. Si aucune capacité n'est disponible, la limite est documentée.

### EF5 – Alternative locale (plan de repli)
Si les crédits ou l'accès Azure sont indisponibles, le sujet autorise une version locale reprenant les mêmes concepts :

| Brique Azure | Équivalent local |
|---|---|
| Azure Data Factory | Apache Airflow (Docker), DAG planifié avec retries |
| Blob Storage / ADLS | Fichiers CSV ou base SQLite |
| Synapse (PySpark) | Python / Pandas |
| Power BI | Jupyter (matplotlib / plotly) ou Tableau Public |

La grille d'évaluation porte sur les services Azure : cette option n'est retenue qu'en dernier recours.

## 7. Exigences non fonctionnelles

| ID | Exigence | Cible |
|---|---|---|
| ENF1 | Latence de bout en bout (source → dashboard) | ≤ 20 min |
| ENF2 | Sécurité | Aucun secret dans le code ; Key Vault et identités managées |
| ENF3 | Coût | Rester dans les crédits étudiants ; auto-pause du Spark pool ; destruction après évaluation |
| ENF4 | Fiabilité | Retry et alertes sur l'ingestion ; traitement rejouable sans doublons |
| ENF5 | Maintenabilité | Code Python modulaire, documenté et formaté (`black`, `ruff`), tests unitaires |
| ENF6 | Traçabilité | Logs d'exécution (volumes, durées, erreurs) consultables |
| ENF7 | Scalabilité | Architecture capable d'absorber un volume ×100 (partitionnement, Spark) |

## 8. Organisation du repo

```
/infra     Terraform (modules, variables, backend)
/adf       Pipelines, datasets, linked services (intégration Git ADF)
/synapse   Notebooks PySpark et scripts SQL
/src       Fonctions Python réutilisables
/tests     Tests unitaires pytest
/powerbi   Fichier .pbix et captures
/docs      Architecture, guide de déploiement, slides
README.md
```

Règles : branches par fonctionnalité, pull requests, commits explicites et réguliers de chaque membre.

## 9. Livrables

| Livrable | Description |
|---|---|
| Repo GitHub (zip) | Code, scripts, documentation et ressources du projet |
| README | Présentation, architecture, procédure de déploiement, captures |
| Démo live | Ingestion → traitement → dashboard sur Azure |
| Présentation | Support type PowerPoint (15 min) |
| Plan B | Vidéo de la démo et captures d'écran |

## 10. Planning

| Semaine | Période | Jalons |
|---|---|---|
| S1 | 21 – 27 oct | Source choisie, repo créé, base Terraform, cahier des charges validé |
| S2 | 28 oct – 3 nov | Ingestion ADF opérationnelle, données dans bronze |
| S3 | 4 – 10 nov | Traitement Synapse (silver/gold) + dashboard Power BI |
| S4 | 11 – 18 nov | Documentation, slides, répétitions, rendu |

## 11. Répartition des rôles

| Membre | Responsabilité principale |
|---|---|
| _à compléter_ | Ingestion (ADF) |
| _à compléter_ | Traitement (Synapse / Python) |
| _à compléter_ | Visualisation (Power BI) |
| _à compléter_ | Infrastructure (Terraform) & documentation |

## 12. Critères d'acceptation (alignés sur le barème)

| Critère | Points | Condition de validation |
|---|---|---|
| Aisance orale | 2 | Présentation fluide, chaque membre intervient |
| Introduction & résumé | 2 | Objectifs, composants et solution Azure présentés clairement |
| Ingestion ADF | 6 | Pipeline planifié, fonctionnel, avec gestion des erreurs |
| Traitement Synapse | 6 | Traitement Python fonctionnel produisant des résultats pertinents |
| Power BI | 4 | Dashboard interactif, actualisé automatiquement, insights mis en avant |
| Q&A | 6 | Réponses précises sur les services et les choix techniques |
| Qualité du code & repo | 2 | Repo structuré, documenté, historique Git propre |
| **Bonus Terraform** | 2 | Déploiement automatisé d'ADF, Synapse et Power BI |

## 13. Risques

| Risque | Impact | Mitigation |
|---|---|---|
| Épuisement des crédits Azure | Élevé | Auto-pause Spark, arrêt des triggers hors démo, alertes de budget |
| Indisponibilité de l'API Vélib' | Moyen | Retry (ADF et client Python), validation des réponses, données d'exemple dans `tests/data/` pour la démo de secours |
| Panne pendant la démo | Élevé | Vidéo et captures de secours, ressources démarrées à l'avance |
| Crédits ou accès Azure indisponibles | Élevé | Activer le Student Pack dès la S1 ; sinon plan de repli local (EF5) |
| Pas de capacité / essai Microsoft Fabric | Moyen | Demander l'essai Fabric avec le compte école ; sinon documenter la limite Terraform pour Power BI |
| Dépendance à un seul membre | Moyen | Revue croisée du code, chacun maîtrise l'ensemble pour le Q&A |
