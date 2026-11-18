# Avancement du projet et passation

> Dernière mise à jour : 8 novembre 2026, par Saer. Points d'étape ajoutés les 16 et 18 novembre (ci-dessous).
> Rendu : **mercredi 18 novembre 2026, 23:59**.

## Point au 18 novembre (jour du rendu)

Toutes les briques techniques sont faites. Il reste la démo et le rendu.

- **Power BI (Saer, PR #10) :** rapport `rpt_velib` dans Fabric (workspace `velib-platform`, capacité d'essai) : Lakehouse `lh_velib` avec 4 raccourcis vers gold, modèle `sm_velib` en Direct Lake, 2 pages (« Réseau en direct », « Analyses »). Détail dans [`powerbi/README.md`](../powerbi/README.md).
- **Vues d'analyse (Saer, PR #9) :** `zone_flow`, `zone_indicators`, `paris_vs_suburbs`, `station_issues` ([`03_create_analysis_views.sql`](../synapse/sql/03_create_analysis_views.sql)).
- **Terraform (Saer, PR #8) :** `apply` du 17 nov fait, drift corrigé (lien Git d'ADF et login SQL de Synapse ignorés). L'alerte et le rôle Synapse d'ADF sont maintenant dans le state : `infra/imports.tf` peut être supprimé.
- **Slides et captures (Saer, PR #10 et #11) :** [`slides_velib.pptx`](slides_velib.pptx) (17 slides) et [`captures/`](captures/).
- **Données :** 53 instantanés dans bronze au 18 nov midi.
- **Avant la démo :** dans ADF Studio, passer `tr_every_15min` à 5 min, le mettre sur *Started* et faire **Publish** (sur Azure il est actuellement *Stopped*, même si `main` indique *Started*). Lancer un run 10 min avant pour que le Spark pool soit chaud.
- **Après la note :** `terraform destroy`, supprimer `rg-velib-tfstate` et le workspace Fabric.

## Point au 16 novembre (Ibrahima)

Les étapes 3 et 4 sont faites et tournent sur Azure. Le détail des tâches est dans [`TODO.md`](../TODO.md).

- **Ingestion ADF :** pipeline `pl_ingest_velib` (ForEach sur les 2 flux → `LookupFeed` → `IfFeedIsValid` → `CopyFeedToBronze`, sinon `FailInvalidFeed` ; `FailIngestion` si l'ingestion échoue). Déclencheur `tr_every_15min` publié et actif. Les JSON sont commités à la racine du repo (root folder `/`, choix final).
- **Traitement Synapse :** notebook `nb_velib_processing`, qui charge [`transform.py`](../src/data_platform_project/transform.py) depuis `synapse/libs/` sur le lac. Silver en Delta incrémental (`MERGE`), 4 tables gold, vues SQL serverless dans la base `velib`.
- **ADF terminé :** le notebook est lancé après chaque ingestion (latence ~3 à 5 min), alerte mail `alert-adf-failed-runs` vers nous deux, linked service Key Vault publié. Penser à arrêter le déclencheur la nuit (*Stop* + *Publish*).
- **Qualité (PR #6) :** CI GitHub Actions (lint, tests, `terraform validate`), rôles dans le cahier des charges, dossier `adf/` supprimé.
- **Pour toi (Saer), au prochain `terraform apply` :** l'alerte mail et le rôle Synapse d'ADF ont été créés à la main puis décrits en Terraform (`monitoring.tf`, `rbac.tf`). [`infra/imports.tf`](../infra/imports.tf) les fait adopter par le state. Ajoute d'abord `alert_emails = ["ibrahima.ndaw@supinfo.com", "saer.diene@supinfo.com"]` dans `terraform.tfvars`, sinon l'apply retire les deux adresses de l'alerte. Après l'apply, supprime `imports.tf`.
- **Reste :** Power BI, slides, répétitions, bonus Fabric.
- **Attention :** l'historique de `main` a été réécrit le 16 nov (3 commits ADF, contenu identique). Avant de pousser : `git fetch && git reset --hard origin/main` si tu n'as rien en local sur `main`.

Ce document résume tout ce qui a été fait, ce qui est déjà en place sur Azure, et ce qu'il reste à faire jusqu'au rendu.

---

## 1. Répartition

| | Saer | Ibrahima |
|---|---|---|
| Étapes | **0 à 2 : faites** ✅ (setup, source, infra Azure) | **3 à 6** : ingestion ADF, traitement Synapse, Power BI, bonus |
| Barème | Terraform (bonus), qualité du repo | Ingestion (6 pts), Synapse (6 pts), Power BI (4 pts) |
| Ensemble | Slides, vidéo de secours, répétitions, rendu | idem |

Le jury peut interroger n'importe lequel de nous deux sur n'importe quelle partie (Q&A = 6 pts). Chacun doit donc comprendre tout le projet, y compris ce document.

---

## 2. Ce qui a été fait

### Étape 0 : structure du repo (PR #1)

| Dossier | Contenu |
|---|---|
| `infra/` | Terraform : **fait** |
| `factory/`, `linkedService/`, `dataset/`, `pipeline/`, `trigger/` | Ressources Data Factory, commitées par l'intégration Git à la racine du repo |
| `synapse/notebooks/`, `synapse/sql/` | Notebooks PySpark, vues SQL serverless : à faire |
| `src/data_platform_project/` | Code Python réutilisable |
| `tests/` | Tests pytest + `tests/data/` (données d'exemple) |
| `powerbi/` | `.pbix` et captures : à faire |
| `docs/` | Documentation |

- Le package Python a été déplacé dans `src/data_platform_project/`, comme l'attend le build `uv_build`.
- Le `.gitignore` exclut `.env`, l'état Terraform (`*.tfstate`, `.terraform/`, `tfplan`), `*.tfvars` et `/data/`.

### Étape 1 : source de données et client Python (PR #2)

**Source : Vélib' Métropole (Paris Open Data, format GBFS).** Elle est publique, sans clé, mise à jour chaque minute, avec des coordonnées GPS et des anomalies naturelles (stations vides, pleines ou hors service).

URL de base : `https://velib-metropole-opendata.smovengo.cloud/opendata/Velib_Metropole`

| Flux | Fichier | Contenu | Fréquence |
|---|---|---|---|
| `station_status` | `station_status.json` | vélos et bornes disponibles par station | ~1 min |
| `station_information` | `station_information.json` | nom, lat/lon, capacité | quasi statique |

Les deux flux se joignent sur `station_id` (~1 520 stations).

Client Python dans [`src/data_platform_project/velib.py`](../src/data_platform_project/velib.py) :

| Fonction | Rôle |
|---|---|
| `fetch_feed(feed)` | télécharge un flux, avec retry automatique (erreurs réseau, 429, 5xx) |
| `validate_payload(feed, payload)` | rejette les réponses vides, mal formées ou incomplètes |
| `bronze_path(feed, ts)` | chemin bronze UTC, par exemple `velib/station_status/2026/11/07/16/05.json` |
| `save_snapshot(out_dir)` | télécharge les deux flux en local, c'est l'équivalent d'ADF (plan B, tests) |

Il y a 15 tests dans [`tests/test_velib.py`](../tests/test_velib.py). Des données d'exemple réelles (20 stations, dont 3 vides, 3 pleines et 2 hors service) sont dans `tests/data/station_status_sample.json` et `tests/data/station_information_sample.json`.

### Étape 2 : infrastructure Azure en Terraform (PR #4) ✅ déployée

Tout est dans [`infra/`](../infra/), avec un guide dans [`infra/README.md`](../infra/README.md).

- Souscription : **Azure for Students** de Saer, tenant **SUPINFO**, avec une limite de dépense active : aucun risque d'être débité.
- Région : **`francecentral`**. La souscription n'autorise que `austriaeast`, `germanywestcentral`, `belgiumcentral`, `francecentral` et `denmarkeast`, et francecentral est la plus proche de Paris avec tous les services nécessaires.

**Ressources créées** (groupe de ressources `rg-velib-platform`) :

| Ressource | Nom | Rôle dans le pipeline |
|---|---|---|
| Data Factory | `adf-velib-mwzyy4` | **Ingestion** : appelle l'API toutes les X min, écrit dans bronze, lance Synapse |
| Data Lake ADLS Gen2 | `stvelibmwzyy4` | **Stockage** : containers `bronze`, `silver`, `gold` (+ `synapse`, interne) |
| Key Vault | `kv-velib-mwzyy4` | **Secrets** : vide pour l'instant (Vélib' n'a pas de clé) |
| Workspace Synapse | `synw-velib-mwzyy4` | **Traitement** : Synapse Studio, SQL serverless |
| Spark pool | `sparkvelib` | **Calcul PySpark** : 3 nœuds Small (12 vCores), Spark 3.4, auto-pause 15 min |
| Budget | `budget-velib` | Alertes par mail à 50, 80 et 100 % de 50 $/mois, envoyées à nous deux |

En plus :
- `rg-velib-tfstate` contient l'**état Terraform** (stockage `sttfstate5fd9bf4a`).
- `synapseworkspace-managedrg-...` est créé automatiquement par Azure : **ne pas y toucher**.

**Points d'accès utiles :**

| | |
|---|---|
| Data Lake (Spark) | `abfss://<bronze\|silver\|gold>@stvelibmwzyy4.dfs.core.windows.net/` |
| Data Lake (ADF) | `https://stvelibmwzyy4.dfs.core.windows.net/` |
| Serveur SQL serverless (Power BI) | `synw-velib-mwzyy4-ondemand.sql.azuresynapse.net` |

**Sécurité** (à savoir pour le Q&A) :
- **Aucune clé, aucun mot de passe.** Les clés du compte de stockage sont désactivées, et Synapse fonctionne en authentification Entra ID uniquement : il n'y a pas d'admin SQL avec mot de passe.
- ADF et Synapse ont chacun une **identité managée** avec les droits *Storage Blob Data Contributor* (Data Lake) et *Key Vault Secrets User*.
- Le pare-feu Synapse est ouvert à toutes les IP, pour qu'on puisse travailler depuis n'importe où. L'accès reste protégé par Entra ID.

---

## 3. Ton accès Azure (Ibrahima)

Tes droits ont été donnés par Terraform :

| Rôle | Sur | Permet |
|---|---|---|
| Contributor | `rg-velib-platform` | gérer toutes les ressources du projet |
| Storage Blob Data Contributor | `stvelibmwzyy4` | lire et écrire dans le Data Lake |
| Key Vault Administrator | `kv-velib-mwzyy4` | gérer les secrets |
| Synapse Administrator | `synw-velib-mwzyy4` | Synapse Studio, notebooks, droits Synapse |

**Pour te connecter :**
1. Va sur https://portal.azure.com avec `ibrahima.ndaw@supinfo.com`.
2. Si tu ne vois pas `rg-velib-platform`, change de répertoire : ⚙️ en haut à droite, *Directories + subscriptions*, puis **SUPINFO**. La souscription « Azure for Students » de Saer apparaît à côté de la tienne.
3. Pour **Synapse Studio** : ouvre `synw-velib-mwzyy4`, puis *Open Synapse Studio*.
4. Pour **ADF Studio** : ouvre `adf-velib-mwzyy4`, puis *Launch Studio*.

**Le crédit est partagé** (celui de Saer, environ 100 $) :
- Le **Spark pool** coûte environ 1,5 à 2 $ par heure quand il tourne. Arrête ta session quand tu as fini (bouton *Stop session*).
- **Désactive le déclencheur ADF** quand on ne travaille pas (la nuit, par exemple).
- Pendant le développement, lance le traitement toutes les 10 à 15 min, **pas toutes les minutes**.

---

## 4. Ce que tu dois faire (Ibrahima)

### Tout de suite (30 min)

- [ ] `git checkout main && git pull`, puis `uv sync` et `uv run pytest` (15 tests doivent passer).
- [ ] **Tester le quota Spark** : dans Synapse Studio, *Develop*, **+**, *Notebook*, *Attach to* `sparkvelib`, puis lance `print("ok")`. Le premier démarrage prend 2 à 3 min. En cas d'erreur de quota, demande une augmentation : portail, *Help + support*, *Create a support request*, *Service and subscription limits (quotas)*, *Azure Synapse Analytics*.
- [ ] Demander l'**essai Microsoft Fabric / Power BI** avec ton mail SUPINFO sur https://app.fabric.microsoft.com.
- [ ] Vérifier que tu as **Power BI Desktop** (Windows uniquement).

### Étape 3 : ingestion ADF (6 pts), branche `feat/adf-ingestion`

Tout se fait dans **ADF Studio** (`adf-velib-mwzyy4`).

1. **Brancher ADF sur GitHub, en premier**, pour que chaque modification soit commitée : *Manage*, *Git configuration*, *Configure*, puis :
   - type GitHub, compte `lambert-19`, repo `my_data_platform` ;
   - collaboration branch : `main`, root folder : `/` (choix final : ADF crée ses dossiers `factory/`, `linkedService/`, `dataset/`, `pipeline/`, `trigger/` à la racine) ;
   - ensuite, travaille sur une branche `feat/adf-ingestion`, créée depuis le menu des branches en haut, et ouvre une PR vers `main` à la fin.

2. **Linked services** (*Manage*, *Linked services*) :
   - **HTTP**, URL de base `https://velib-metropole-opendata.smovengo.cloud/opendata/Velib_Metropole/`, authentification *Anonymous* ;
   - **Azure Data Lake Storage Gen2**, URL `https://stvelibmwzyy4.dfs.core.windows.net/`, authentification **System-assigned managed identity**. Les droits sont déjà donnés, et les clés du compte sont désactivées : ne choisis pas « Account key » ;
   - **Azure Key Vault**, `kv-velib-mwzyy4`, en identité managée. Pas indispensable pour Vélib', mais exigé par le cahier des charges.

3. **Datasets** :
   - source : JSON sur le linked service HTTP, avec un paramètre `feed` et l'URL relative `@{dataset().feed}.json` ;
   - destination : JSON sur ADLS Gen2, container `bronze`, avec un paramètre de chemin.

4. **Pipeline `pl_ingest_velib`** :
   - un paramètre `feeds` = `["station_status", "station_information"]` ;
   - un **ForEach** sur `feeds`, contenant une activité **Copy** ;
   - le chemin de destination doit suivre le même découpage que `bronze_path()` en Python :
     ```
     @concat('velib/', item(), '/', formatDateTime(pipeline().TriggerTime, 'yyyy/MM/dd/HH'), '/', formatDateTime(pipeline().TriggerTime, 'mm'), '.json')
     ```
   - sur la Copy : **Retry = 3**, **Retry interval = 30 s**, **Timeout = 5 min**.

5. **Validation** (exigence EF1.5) : avant ou après la Copy, une activité **Lookup** ou **Web** lit la réponse, puis une **If Condition** vérifie que `data.stations` n'est pas vide. Si la réponse est vide, l'activité **Fail** arrête le pipeline avec un message clair. Les règles à reproduire sont dans `validate_payload()` de `velib.py`.

6. **Gestion des erreurs et alerte** :
   - un chemin *On failure* qui journalise l'erreur, par exemple avec une activité *Set variable* ;
   - une **alerte mail** : *Monitor*, *Alerts & metrics*, *New alert rule*, métrique *Failed pipeline runs* supérieure à 0, avec notification par mail à nous deux.

7. **Déclencheur** : un *Schedule trigger* **toutes les 5 min**. Il faut pouvoir le justifier : la source change chaque minute, mais 5 min est un bon compromis entre fraîcheur et coût, et on reste sous les 20 min de latence exigées.

8. **Lancer Synapse après l'ingestion** (exigence EF1.6), une fois l'étape 4 prête :
   - ajoute une activité **Synapse notebook** à la fin du pipeline, sur un linked service *Azure Synapse Analytics* (workspace `synw-velib-mwzyy4`) en identité managée ;
   - ADF a besoin d'un **rôle Synapse** pour lancer un notebook. Tu es Synapse Administrator, donc tu peux le lui donner : Synapse Studio, *Manage*, *Access control*, *Add*, rôle *Synapse Administrator* (le plus simple), membre `adf-velib-mwzyy4` ;
   - pour limiter les coûts, ne lance le notebook qu'**une fois sur deux ou trois**, ou crée un second déclencheur toutes les 15 min.

9. **Captures pour le README et la démo** : exécutions réussies dans *Monitor*, fichiers dans `bronze/` (*Storage browser* du compte `stvelibmwzyy4`).

### Étape 4 : traitement Synapse (6 pts), branche `feat/synapse-processing`

**Commence en local avec `tests/data/`.** Tu n'as pas besoin d'attendre qu'ADF tourne.

1. Écris les transformations comme des **fonctions PySpark pures** dans `src/data_platform_project/transform.py`, avec leurs tests dans `tests/test_transform.py`. En local, PySpark a besoin de Java 17 (`java -version`).

2. **Bronze → silver** :
   - exploser `data.stations` : une ligne par station et par instantané ;
   - convertir `last_reported` (epoch en secondes) en timestamp UTC ;
   - extraire vélos mécaniques et électriques de `num_bikes_available_types`. C'est une liste de dictionnaires : `[{"mechanical": 10}, {"ebike": 2}]` ;
   - ignorer les doublons en camelCase (`numBikesAvailable`, `numDocksAvailable`) ;
   - joindre `station_information` sur `station_id` pour avoir nom, lat/lon et capacité ;
   - ajouter l'horodatage d'ingestion (tiré du chemin bronze) ;
   - dédoublonner sur (`station_id`, horodatage d'ingestion) : une station qui ne change pas garde le même `last_reported`, et dédoublonner sur ce champ la ferait disparaître des instantanés suivants ;
   - gérer les valeurs manquantes.

3. **Silver → gold** (KPI) :
   - taux d'occupation = vélos / capacité (par station et global) ;
   - nombre de stations vides, pleines et hors service ;
   - moyenne glissante des vélos disponibles (30 min ou 1 h) ;
   - répartition par zone : les 2 premiers chiffres de `stationCode` semblent donner l'arrondissement pour Paris intra-muros, **à vérifier** ;
   - anomalies : station vide ou pleine depuis plus de X min, chute brutale, station hors service.

4. Format **Delta** (ou Parquet), partitionné par date, dans `silver/` et `gold/`.

5. **Incrémental et rejouable sans doublons** (exigences EF2.3 et ENF4) : watermark sur la date d'ingestion, ou Structured Streaming avec checkpoint.

6. **Logs** : lignes en entrée et en sortie, durée, latence de bout en bout.

7. Dans Synapse Studio, active aussi l'**intégration Git** (*Manage*, *Git configuration*, même repo, **root folder `/synapse`**), puis crée les notebooks. Ils lisent et écrivent en `abfss://...@stvelibmwzyy4.dfs.core.windows.net/`.

### Étape 5 : SQL serverless + Power BI (4 pts), branche `feat/powerbi-dashboard`

1. Vues SQL serverless sur `gold` (`OPENROWSET`, format Delta ou Parquet) dans une base dédiée, par exemple `velib`. Scripts dans `synapse/sql/`.
2. Power BI Desktop : *Get data*, *Azure Synapse Analytics SQL*, serveur `synw-velib-mwzyy4-ondemand.sql.azuresynapse.net`, mode **DirectQuery**, connexion avec ton compte SUPINFO.
3. Visuels attendus :
   - cartes KPI ;
   - courbe dans le temps ;
   - **carte des stations** (lat/lon) ;
   - filtres (date, zone, type de vélo) ;
   - anomalies mises en évidence ;
   - encart « insights clés ».
4. **Actualisation automatique de page** : avec une licence Pro, le minimum est de 30 min. Pour quelques minutes, publie dans un **workspace Fabric** (essai).
5. Publie le rapport, puis mets le `.pbix` et des captures dans `powerbi/`.

### Étape 6 : bonus Fabric + doc, branche `feat/infra-fabric`

- Workspace Fabric en Terraform (provider `microsoft/fabric`), dans un **dossier séparé `infra/fabric/`** avec sa propre clé de state (`key = "fabric.tfstate"` dans un `backend.hcl` dédié). Comme ça, tu ne touches pas à l'infra principale. Lancer `terraform apply` sur `infra/` demande le rôle Owner, que seul Saer a.
- Pour lire et écrire l'état Terraform, Saer doit te donner l'accès au stockage du state (voir section 6).
- Compléter le README : schéma d'architecture, procédure de déploiement, captures.

---

## 5. Comment on travaille sur le repo

```bash
uv sync                                    # dépendances
uv run pytest                              # tests
uv run ruff check . && uv run black .      # lint + formatage avant chaque commit
uv run python -m data_platform_project.velib   # télécharger un vrai instantané dans data/bronze/
```

Workflow git :
1. Une branche par étape depuis `main` à jour (`git checkout main && git pull && git checkout -b feat/...`).
2. Des commits réguliers avec un préfixe : `feat:`, `fix:`, `test:`, `docs:`, `chore:`.
3. `git push -u origin <branche>`, puis `gh pr create --fill --base main`.
4. Chacun merge ses propres PR. L'autre relit après coup, ce qui sert aussi de préparation au Q&A.
5. Jamais de secret dans le code.

Pour ADF et Synapse, l'intégration Git commite directement depuis l'interface web sur ta branche. Tu n'as plus qu'à ouvrir la PR.

---

## 6. Calendrier

| Dates | Ibrahima | Saer |
|---|---|---|
| 8–9 nov | Accès Azure, test du quota Spark, **étape 3 : ADF** | Accès au state Terraform pour Ibrahima, relecture |
| 9–12 nov | **Étape 4 : Synapse** (commencée en local en parallèle) | Relecture, préparation des slides |
| 12–14 nov | **Étape 5 : SQL + Power BI** | Relecture, slides |
| 14–15 nov | **Étape 6 : bonus Fabric + README** | Relecture |
| 16–17 nov | **Ensemble** : slides, vidéo de secours de la démo, 2 répétitions chronométrées | |
| 18 nov | **Ensemble** : vérifier qu'aucun secret n'est commité, zip, rendu. Après la note, Saer lance `terraform destroy` et supprime `rg-velib-tfstate` | |

Références : [`CAHIER_DES_CHARGES.md`](../CAHIER_DES_CHARGES.md) pour les exigences et [`TODO.md`](../TODO.md) pour les tâches détaillées et les questions probables du jury.
