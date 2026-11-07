# Avancement du projet et passation

> Dernière mise à jour : 7 novembre 2026, par Saer.
> Rendu : **mercredi 18 novembre 2026, 23:59**.

Ce document résume ce qui a été fait étape par étape, comment on travaille sur le repo, et ce que chacun doit faire jusqu'au rendu.

---

## 1. Répartition du travail

On coupe le pipeline en deux moitiés. Chacun avance sans attendre l'autre.

| | Saer | Ibrahima |
|---|---|---|
| Étapes | 0 à 3 : setup, source, infra, ingestion | 4 à 6 : traitement, dashboard, bonus |
| Partie du barème | Ingestion ADF (6 pts), Terraform | Synapse (6 pts), Power BI (4 pts), bonus Fabric |
| Ensemble | Slides, vidéo de secours, répétitions, rendu | idem |

Le jury peut interroger n'importe lequel de nous deux sur n'importe quelle partie (Q&A = 6 pts). On relit donc les PR l'un de l'autre, même après le merge.

---

## 2. Ce qui a été fait

### Étape 0 : structure du repo (PR #1, mergée)

- Arborescence prévue par le cahier des charges :

  | Dossier | Contenu |
  |---|---|
  | `infra/` | Terraform |
  | `adf/` | Pipelines Data Factory (intégration Git) |
  | `synapse/notebooks/`, `synapse/sql/` | Notebooks PySpark, vues SQL serverless |
  | `src/data_platform_project/` | Code Python réutilisable |
  | `tests/` | Tests pytest (+ `tests/data/` : données d'exemple) |
  | `powerbi/` | `.pbix` et captures |
  | `docs/` | Documentation (ce fichier) |

- **Package Python corrigé.** Le code était dans `src/__init__.py`. Le build `uv_build` attend `src/data_platform_project/`, donc on l'a déplacé. `uv run data-platform-project` fonctionne maintenant.
- **`.gitignore`** : il exclut `.env`, les fichiers d'état Terraform (`*.tfstate`, `.terraform/`), `*.tfvars` (seul `*.tfvars.example` est versionné) et `/data/` (instantanés téléchargés en local).
- **README** : squelette, à compléter au fil du projet.

### Étape 1 : source de données et client Python (PR #2, mergée)

**Source choisie : Vélib' Métropole (Paris Open Data, format GBFS).**

Pourquoi ce choix :
- l'API est publique, **sans clé** et sans limite de requêtes gênante ;
- les données sont mises à jour **chaque minute**, ce qui est idéal pour une démo en temps réel ;
- chaque station a des **coordonnées GPS**, ce qui permet une carte dans Power BI ;
- il y a des **anomalies naturelles** : stations vides, pleines ou hors service.

Deux flux, à joindre sur `station_id` :

| Flux | URL | Contenu | Fréquence |
|---|---|---|---|
| `station_status` | `.../Velib_Metropole/station_status.json` | vélos et bornes disponibles | ~1 min |
| `station_information` | `.../Velib_Metropole/station_information.json` | nom, GPS, capacité | quasi statique |

URL de base : `https://velib-metropole-opendata.smovengo.cloud/opendata/Velib_Metropole`

Le client Python est dans [`src/data_platform_project/velib.py`](../src/data_platform_project/velib.py) :

| Fonction | Rôle |
|---|---|
| `fetch_feed(feed)` | télécharge un flux, avec retry automatique sur les erreurs réseau et les codes 429/5xx |
| `validate_payload(feed, payload)` | rejette les réponses vides, mal formées ou incomplètes (exigence EF1.5) |
| `bronze_path(feed, ts)` | donne le chemin bronze partitionné, par exemple `velib/station_status/2026/11/07/16/05.json` (UTC) |
| `save_snapshot(out_dir)` | télécharge les deux flux et les écrit tels quels, c'est l'équivalent local d'ADF |

Tests : [`tests/test_velib.py`](../tests/test_velib.py), 15 tests qui n'appellent jamais la vraie API.

**Données d'exemple pour le traitement**, extraites de vraies réponses :
- `tests/data/station_status_sample.json`
- `tests/data/station_information_sample.json`

Elles contiennent 20 stations, dont 3 vides (`num_bikes_available = 0`), 3 pleines (`num_docks_available = 0`) et 2 hors service (`is_installed = 0` ou `is_renting = 0`).

### Préparation Azure (côté Saer)

- Souscription : **Azure for Students**, tenant **SUPINFO**.
- Régions autorisées par la souscription : `austriaeast`, `germanywestcentral`, `belgiumcentral`, `francecentral`, `denmarkeast`.
- **Région retenue : `francecentral`.** C'est la plus proche de Paris, et tous les services nécessaires y sont disponibles (ADLS Gen2, Key Vault, Data Factory, Synapse + Spark pool).
- Azure CLI installé et connecté. Terraform est la prochaine étape.

---

## 3. Comment on travaille sur le repo

### Lancer le projet en local

Prérequis : Python 3.13 et [uv](https://docs.astral.sh/uv/).

```bash
uv sync                                   # dépendances (pandas, requests, pyspark, pytest, ruff, black)
uv run pytest                             # tous les tests
uv run pytest tests/test_velib.py::test_bronze_path_is_utc_partitioned   # un seul test
uv run ruff check . && uv run black .     # lint + formatage (à faire avant chaque commit)
uv run python -m data_platform_project.velib   # télécharger un vrai instantané dans data/bronze/
```

PySpark a besoin de Java en local (`java -version`). S'il manque : installe Java 17 (Temurin, par exemple).

### Workflow git

1. Une branche par étape, créée depuis `main` à jour :
   ```bash
   git checkout main && git pull
   git checkout -b feat/synapse-processing
   ```
2. Des commits réguliers et explicites, avec un préfixe : `feat:`, `fix:`, `test:`, `docs:`, `chore:`. Exemple : `feat(synapse): add bronze to silver notebook`.
3. Push puis PR :
   ```bash
   git push -u origin feat/synapse-processing
   gh pr create --fill --base main
   ```
4. **Chacun merge ses propres PR** pour ne pas bloquer l'autre. L'autre relit après coup.
5. Jamais de secret dans le code : clés et mots de passe vont dans Key Vault.

---

## 4. Ce qu'il reste à faire

### Saer : étapes 2 et 3

| # | Étape | Branche | Ce que ça débloque pour Ibrahima |
|---|---|---|---|
| 2 | **Terraform** : state distant, groupe de ressources, ADLS Gen2 (containers `bronze`/`silver`/`gold`), Key Vault, Data Factory, Synapse workspace + Spark pool (auto-pause), droits d'accès | `feat/infra-terraform` | le workspace Synapse et le Data Lake existent |
| 3 | **ADF** : Copy des deux flux vers `bronze/velib/<flux>/yyyy/MM/dd/HH/mm.json`, déclencheur **toutes les 5 min**, retry, validation, alerte en cas d'échec, intégration Git dans `adf/`. Le pipeline déclenche ensuite le notebook Synapse. | `feat/adf-ingestion` | des fichiers arrivent en continu dans bronze |

Dès que l'étape 2 est faite, Saer **ajoute Ibrahima avec le rôle Contributor** sur le groupe de ressources, pour qu'il accède à Synapse. Saer lui envoie aussi le nom du compte de stockage et du workspace.

### Ibrahima : étapes 4, 5 et 6

#### À faire tout de suite (sans Azure)

- [ ] Récupérer `main` à jour, puis vérifier `uv sync` et `uv run pytest`.
- [ ] Demander l'**essai Microsoft Fabric / Power BI** avec ton mail SUPINFO sur https://app.fabric.microsoft.com.
- [ ] Vérifier que tu as **Power BI Desktop** (Windows uniquement : Saer est sur Mac).

#### Étape 4 : traitement Synapse (6 pts), branche `feat/synapse-processing`

**Commence en local avec les données d'exemple.** Tu n'as pas besoin d'attendre Azure.

1. Écris les transformations comme des **fonctions PySpark pures** (DataFrame en entrée, DataFrame en sortie) dans `src/data_platform_project/transform.py`, avec leurs tests dans `tests/test_transform.py`. Les notebooks Synapse ne feront qu'appeler ces fonctions.

2. **Bronze → silver** :
   - exploser `data.stations` (une ligne par station et par instantané) ;
   - convertir `last_reported` (epoch en secondes) en timestamp UTC ;
   - extraire les vélos mécaniques et électriques de `num_bikes_available_types`. Attention, c'est une liste de dictionnaires : `[{"mechanical": 10}, {"ebike": 2}]` ;
   - ignorer les doublons en camelCase (`numBikesAvailable`, `numDocksAvailable`) ;
   - joindre avec `station_information` sur `station_id` pour avoir nom, GPS et capacité ;
   - ajouter un horodatage d'ingestion (tiré du chemin du fichier ou de l'heure de traitement) ;
   - dédoublonner sur (`station_id`, `last_reported`), car une station qui n'a pas changé renvoie le même `last_reported` ;
   - gérer les valeurs manquantes.

3. **Silver → gold** : les KPI. Idées :
   - taux d'occupation = vélos / capacité, par station et global ;
   - nombre de stations vides, pleines et hors service ;
   - moyenne glissante des vélos disponibles (par exemple sur 30 min ou 1 h) ;
   - répartition par zone. Les 2 premiers chiffres de `stationCode` semblent correspondre à l'arrondissement pour Paris intra-muros, **à vérifier** ;
   - anomalies : station vide ou pleine depuis plus de X minutes, chute brutale du nombre de vélos, station hors service.

4. Format : **Delta** (ou Parquet) partitionné par date, dans `silver/` et `gold/`.

5. **Traitement incrémental** : ne traiter que les nouveaux fichiers bronze, par exemple avec un watermark sur la date d'ingestion ou Spark Structured Streaming avec checkpoint. Le traitement doit pouvoir être relancé **sans créer de doublons** (exigence ENF4).

6. Ajoute des **logs** : nombre de lignes en entrée et en sortie, durée, latence.

7. Une fois Azure prêt, crée les notebooks dans `synapse/notebooks/` (ou via l'intégration Git de Synapse) et lis les données en `abfss://<container>@<compte>.dfs.core.windows.net/...`.

> 💰 **Coût** : le Spark pool coûte cher et met 2 à 3 min à démarrer. Garde l'auto-pause à 15 min. Pour le traitement, vise toutes les 10 à 15 min, pas chaque minute. On reste sous les 20 min de latence exigées.

#### Étape 5 : SQL serverless + Power BI (4 pts), branche `feat/powerbi-dashboard`

1. Écris les **vues SQL serverless** sur la couche gold (`OPENROWSET` sur Delta/Parquet) dans `synapse/sql/`.
2. Dans Power BI Desktop, connecte-toi au point de terminaison serverless de Synapse en **DirectQuery**.
3. Visuels attendus :
   - cartes KPI : vélos disponibles, taux d'occupation, stations vides ou pleines ;
   - courbe dans le temps ;
   - **carte des stations** (lat/lon) ;
   - filtres : date, zone, type de vélo ;
   - mise en évidence des anomalies ;
   - encart « insights clés ».
4. **Actualisation automatique de page**. Sur une capacité partagée (licence Pro), l'intervalle minimum est de 30 min. Pour descendre à quelques minutes, publie le rapport dans un **workspace Fabric** (essai). L'essai Fabric est donc important.
5. Publie le rapport sur le Power BI Service, puis mets le `.pbix` et des captures dans `powerbi/`.

#### Étape 6 : bonus et doc, branche `feat/infra-fabric`

- Workspace Fabric en Terraform (provider `microsoft/fabric`) dans `infra/`, rattaché à la capacité d'essai. Si ce n'est pas possible, documenter la limite.
- Compléter le README : schéma d'architecture, procédure de déploiement, captures.

---

## 5. Calendrier

| Dates | Saer | Ibrahima |
|---|---|---|
| 7–9 nov | Étape 2 : Terraform | Étape 4 en local avec les données d'exemple |
| 9–11 nov | Étape 3 : ingestion ADF | Étape 4 : brancher sur Synapse |
| 12–14 nov | Alertes, monitoring, README | Étape 5 : vues SQL + Power BI |
| 14–15 nov | Aide sur le bonus si besoin | Étape 6 : bonus Fabric |
| 16–17 nov | **Ensemble** : slides, vidéo de secours, 2 répétitions chronométrées | |
| 18 nov | **Ensemble** : vérifier qu'aucun secret n'est commité, zip, rendu. Après la note : `terraform destroy` | |

Le cahier des charges complet est dans [`CAHIER_DES_CHARGES.md`](../CAHIER_DES_CHARGES.md), et la liste détaillée des tâches et des questions probables du jury dans [`TODO.md`](../TODO.md).
