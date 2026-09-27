<div align="center">

# Customer Churn Prediction

### Anticiper le risque de départ pour mieux accompagner les clients

Application de prédiction du churn télécom construite avec **Python**, **scikit-learn**, **FastAPI** et une interface web responsive.

[![CI](https://github.com/yahia-khroufi/Customer-Churn-Prediction/actions/workflows/ci.yml/badge.svg)](https://github.com/yahia-khroufi/Customer-Churn-Prediction/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.14-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Azure](https://img.shields.io/badge/Cloud-Microsoft%20Azure-0078D4?logo=microsoftazure&logoColor=white)](https://azure.microsoft.com/)

</div>

## À propos

Ce projet entraîne plusieurs classifieurs sur des données de clients télécoms, sélectionne le meilleur pipeline selon le **F1-score**, puis expose la prédiction via une API REST. L’interface permet de renseigner un profil client, de consulter la probabilité de churn et de télécharger le résultat.

### Points clés

- validation des **19 caractéristiques** client avant prédiction ;
- comparaison de quatre modèles : régression logistique, arbre de décision, forêt aléatoire et XGBoost ;
- prétraitement numérique et catégoriel encapsulé dans un pipeline scikit-learn ;
- API documentée automatiquement avec OpenAPI ;
- interface responsive pour ordinateur et mobile ;
- déploiement conteneurisé sur Azure Container Apps avec Terraform et GitHub Actions.

## Sommaire

- [Aperçu de l’application](#aperçu-de-lapplication)
- [Résultats du modèle](#résultats-du-modèle)
- [Fonctionnement](#fonctionnement)
- [Démarrage local](#démarrage-local)
- [API et prédiction](#api-et-prédiction)
- [CI/CD et infrastructure Azure](#cicd-et-infrastructure-azure)
- [Organisation du dépôt](#organisation-du-dépôt)
- [Limites](#limites)

## Aperçu de l’application

L’interface est conçue autour d’un parcours simple : renseigner un profil, lancer l’analyse, puis interpréter le score avec le contexte du modèle. Chaque capture peut être ouverte en taille réelle.

<table>
  <tr>
    <td align="center"><strong>Formulaire client · Desktop</strong></td>
    <td align="center"><strong>Résultat · Desktop</strong></td>
    <td align="center"><strong>Résultat · Mobile</strong></td>
  </tr>
  <tr>
    <td align="center">
      <a href="artifacts/screenshots/desktop-form.png">
        <img src="artifacts/screenshots/desktop-form.png" alt="Formulaire de profil client sur ordinateur" width="360">
      </a>
    </td>
    <td align="center">
      <a href="artifacts/screenshots/desktop-result.png">
        <img src="artifacts/screenshots/desktop-result.png" alt="Résultat de prédiction sur ordinateur" width="360">
      </a>
    </td>
    <td align="center">
      <a href="artifacts/screenshots/mobile-result.png">
        <img src="artifacts/screenshots/mobile-result.png" alt="Résultat de prédiction sur mobile" width="112">
      </a>
    </td>
  </tr>
</table>

> Le score de churn est une estimation statistique destinée à aider l’analyse. Il ne constitue pas une certitude ni une décision automatique concernant un client.

## Résultats du modèle

Le rapport versionné [`models/churn_pipeline.json`](models/churn_pipeline.json) décrit le modèle actuellement enregistré : une **régression logistique** évaluée sur **1 409 clients** réservés au test.

| Indicateur | Résultat |
| :--- | ---: |
| Exactitude | **74,2 %** |
| Précision | **50,9 %** |
| Rappel | **78,6 %** |
| F1-score | **0,618** |
| ROC-AUC | **0,841** |

La classe `Yes` est prédite lorsque la probabilité dépasse le seuil de **0,5**. Un nouvel entraînement peut produire un modèle ou des scores différents.

## Fonctionnement

```text
data/raw/churn.csv
        │
        ▼
Validation et préparation des 19 caractéristiques
        │
        ▼
Comparaison de 4 classifieurs par validation croisée
        │
        ▼
Recherche de paramètres sur les 2 meilleurs modèles
        │
        ▼
Évaluation sur un jeu de test réservé
        │
        ▼
Pipeline joblib + rapport JSON
        │
        ▼
API FastAPI + interface web responsive
```

Les transformations apprises à l’entraînement sont réutilisées à l’identique au moment de la prédiction. Cette approche évite les divergences entre le traitement des données d’entraînement et celui des données envoyées à l’API.

## Démarrage local

### Prérequis

- Python **3.14**
- `pip`
- Docker Desktop, uniquement pour le démarrage avec Docker Compose

### Installation et lancement

Depuis la racine du dépôt :

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python run_pipeline.py --evaluate
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

Ouvrir ensuite :

- application : [http://127.0.0.1:8000](http://127.0.0.1:8000) ;
- documentation interactive : [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

La commande d’entraînement crée `models/churn_pipeline.joblib` et met à jour `models/churn_pipeline.json`. Le fichier `.joblib` est ignoré par Git : il doit être généré avant de lancer l’application ou de construire l’image Docker.

### Avec Docker Compose

Après avoir généré le modèle :

```powershell
docker compose up --build
```

L’application est accessible sur [http://127.0.0.1:8000](http://127.0.0.1:8000). Le conteneur expose également le contrôle de santé `/health`.

## API et prédiction

| Méthode | Route | Description |
| :---: | :--- | :--- |
| `GET` | `/` | Interface web |
| `GET` | `/health` | État de l’API et du modèle |
| `GET` | `/schema` | Caractéristiques et valeurs autorisées |
| `GET` | `/model-info` | Modèle et métriques disponibles |
| `POST` | `/predict` | Prédiction pour un profil client |
| `GET` | `/docs` | Documentation OpenAPI interactive |

### Exemple de requête

Le dépôt contient un profil prêt à l’emploi dans [`examples/customer.json`](examples/customer.json) :

```powershell
curl.exe -X POST http://127.0.0.1:8000/predict `
  -H "Content-Type: application/json" `
  --data-binary "@examples/customer.json"
```

La réponse contient notamment :

```json
{
  "prediction": "Yes",
  "churn_probability": 0.899,
  "threshold": 0.5,
  "model_name": "LogisticRegression"
}
```

Pour lancer une prédiction directement depuis la ligne de commande :

```powershell
python -m src.models.predict examples/customer.json
```

L’API refuse les combinaisons incohérentes de services téléphoniques ou Internet. `TotalCharges` peut être omis ; le pipeline traite alors la valeur manquante.

## CI/CD et infrastructure Azure

Le déploiement utilise **GitHub Actions**, l’authentification Azure **OIDC**, **Terraform**, **Azure Container Registry** et **Azure Container Apps**.

### Architecture de déploiement

```text
Push sur main
     │
     ▼
CI : tests Python + validation Terraform
     │
     ▼
CD : build de l’image + push vers ACR
     │
     ▼
Azure Container Apps
     │
     ├── dev
     ├── staging
     └── production
```

### Ressources Azure

La capture ci-dessous présente les ressources provisionnées dans Azure Resource Manager.

<p align="center">
  <a href="artifacts/screenshots/azure-resources.png">
    <img src="artifacts/screenshots/azure-resources.png" alt="Ressources Azure du projet Customer Churn" width="900">
  </a>
</p>
<p align="center"><em>Ressources Azure : Container Registry, Container App, Log Analytics, identités managées, environnement Container Apps et stockage d’état Terraform.</em></p>

| Workflow | Déclenchement | Rôle |
| :--- | :--- | :--- |
| [CI](.github/workflows/ci.yml) | Pull request et push sur `main` | Tests Python et validation Terraform |
| [CD](.github/workflows/cd.yml) | CI réussi après un push sur `main` | Déploiement successif vers `dev`, `staging`, puis `production` |
| [Infrastructure](.github/workflows/infra-deploy.yml) | Déclenchement manuel | Provisionnement Terraform de l’environnement choisi |

La configuration est détaillée dans [`.azure/pipeline-setup.md`](.azure/pipeline-setup.md). Les commandes Terraform locales sont disponibles dans [`deploy/terraform/README.md`](deploy/terraform/README.md).

> **État au 27 septembre 2026.** Le déploiement `dev` a réussi et son endpoint `/health` répond. `staging` est bloqué par des variables d’environnement GitHub non configurées ; `production` reste donc en attente. Chaque environnement doit disposer de ses identités fédérées, droits Azure, ressources applicatives et clé d’état Terraform.

## Organisation du dépôt

```text
api/                    API FastAPI et interface web
artifacts/screenshots/  Captures de l’interface et de l’infrastructure Azure
data/raw/               Jeu de données d’entraînement
deploy/terraform/       Infrastructure Azure
examples/               Exemple de profil client JSON
models/                 Rapport du modèle ; pipeline joblib généré localement
notebooks/              Exploration des données
src/common/             Contrat de données
src/data/               Nettoyage et prétraitement
src/models/             Entraînement, évaluation, prédiction et suivi MLflow
tests/                  Tests de l’application et du pipeline
```

## Limites

Les performances affichées proviennent d’un jeu de test réservé et ne garantissent pas les performances sur de nouvelles populations. Le résultat individuel est un signal d’aide à l’analyse : il ne mesure ni la cause du départ ni l’effet d’une action commerciale. Le modèle et ses métriques doivent être réévalués lorsque les données évoluent.
