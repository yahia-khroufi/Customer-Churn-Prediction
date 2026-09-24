# Configuration CI/CD GitHub Actions

La pipeline utilise trois workflows :

- `CI` exécute les tests Python sur les pull requests et les push vers `main`.
- `CD` déploie séquentiellement vers `dev`, `staging`, puis `production`.
- `Infrastructure` provisionne manuellement Terraform pour un environnement choisi.

Une pull request ne déclenche jamais de déploiement.

## 1. Créer l'identité du pipeline

L'identité utilisée par GitHub Actions doit être **différente** de
`customer-churn-pull`, qui sert uniquement au pull d'image de la Container App.

Depuis WSL ou Azure Cloud Shell, définir les variables :

```bash
SUBSCRIPTION_ID="35726a57-2e04-4b2d-afb2-d8373578a5db"
PIPELINE_RG="rg-customer-churn-github"
IDENTITY_NAME="id-customer-churn-github"
```

Créer le groupe et l'identité :

```bash
az group create --name "$PIPELINE_RG" --location germanywestcentral
az identity create --name "$IDENTITY_NAME" --resource-group "$PIPELINE_RG"
CLIENT_ID=$(az identity show --name "$IDENTITY_NAME" --resource-group "$PIPELINE_RG" --query clientId -o tsv)
PRINCIPAL_ID=$(az identity show --name "$IDENTITY_NAME" --resource-group "$PIPELINE_RG" --query principalId -o tsv)
TENANT_ID=$(az account show --query tenantId -o tsv)
```

Donner à l'identité les droits de déploiement sur le groupe applicatif :

```bash
APP_RG_ID=$(az group show --name rg-customer-churn --query id -o tsv)
az role assignment create --assignee-object-id "$PRINCIPAL_ID" \
  --assignee-principal-type ServicePrincipal --role Contributor --scope "$APP_RG_ID"

ACR_ID=$(az acr show --name churnyahia2026 --resource-group rg-customer-churn --query id -o tsv)
az role assignment create --assignee-object-id "$PRINCIPAL_ID" \
  --assignee-principal-type ServicePrincipal --role AcrPush --scope "$ACR_ID"
```

Le rôle `Contributor` couvre le provisionnement Terraform et le déploiement de
la Container App. L'image est poussée par le pipeline via `az acr login`.

## 2. Créer le backend Terraform distant

L'état Terraform doit être partagé entre les runners GitHub. Créer une fois un
compte de stockage dédié dans le groupe du pipeline :

```bash
STATE_STORAGE="stcustomerchurntf2026"
az storage account create --name "$STATE_STORAGE" \
  --resource-group "$PIPELINE_RG" --location germanywestcentral \
  --sku Standard_LRS --kind StorageV2 --allow-blob-public-access false
az storage container create --name tfstate \
  --account-name "$STATE_STORAGE" --auth-mode login
STATE_STORAGE_ID=$(az storage account show --name "$STATE_STORAGE" \
  --resource-group "$PIPELINE_RG" --query id -o tsv)
az role assignment create --assignee-object-id "$PRINCIPAL_ID" \
  --assignee-principal-type ServicePrincipal \
  --role "Storage Blob Data Contributor" --scope "$STATE_STORAGE_ID"
```

Le nom du compte doit être globalement unique et contenir uniquement des lettres
minuscules et des chiffres. Le verrouillage de l'état est géré par le backend
Azure Blob.

Comme l'infrastructure existe déjà, migrer une fois l'état Terraform local vers
ce backend avant le premier lancement GitHub Actions :

```bash
cd deploy/terraform
terraform init -migrate-state \
  -backend-config="resource_group_name=$PIPELINE_RG" \
  -backend-config="storage_account_name=$STATE_STORAGE" \
  -backend-config="container_name=tfstate" \
  -backend-config="key=customer-churn-dev.tfstate"
```

Répondre `yes` à la migration. Pour `staging` et `production`, utiliser des
états séparés et importer/provisionner leurs ressources correspondantes.

## 3. Configurer les identités fédérées

Créer une crédentielle fédérée par environnement, avec l'émetteur et l'audience
GitHub standard :

```bash
for ENV in dev staging production; do
  az identity federated-credential create \
    --name "github-$ENV" \
    --identity-name "$IDENTITY_NAME" \
    --resource-group "$PIPELINE_RG" \
    --issuer https://token.actions.githubusercontent.com \
    --subject "repo:OWNER/REPOSITORY:environment:$ENV" \
    --audiences api://AzureADTokenExchange
done
```

Remplacer `OWNER/REPOSITORY` par le dépôt GitHub réel.

## 4. Créer les environnements GitHub

Dans GitHub : `Settings > Environments`, créer :

- `dev`
- `staging`
- `production`

Ajouter une règle d'approbation obligatoire à `staging` et `production`.
Vous pouvez aussi protéger `dev` si vous souhaitez valider chaque déploiement.

Dans chaque environnement, ajouter ces **variables** :

| Variable | Exemple pour l'environnement actuel |
|---|---|
| `AZURE_CLIENT_ID` | client ID de `id-customer-churn-github` |
| `AZURE_TENANT_ID` | tenant ID Azure |
| `AZURE_SUBSCRIPTION_ID` | ID de l'abonnement |
| `AZURE_LOCATION` | `germanywestcentral` |
| `AZURE_RESOURCE_GROUP` | `rg-customer-churn` |
| `AZURE_REGISTRY_NAME` | `churnyahia2026` |
| `AZURE_CONTAINER_ENVIRONMENT` | `env-customer-churn` |
| `AZURE_CONTAINER_APP` | `customer-churn` |
| `AZURE_TFSTATE_RESOURCE_GROUP` | `rg-customer-churn-github` |
| `AZURE_TFSTATE_STORAGE_ACCOUNT` | `stcustomerchurntf2026` |
| `AZURE_TFSTATE_CONTAINER` | `tfstate` |
| `AZURE_TFSTATE_KEY` | `customer-churn-dev.tfstate` |

Pour de vrais environnements séparés, mettre un groupe, un ACR, un
Container Apps Environment et une Container App différents dans chaque
environnement GitHub. Utiliser aussi une clé d'état différente par environnement.

## 5. Premier lancement

1. Configurer les variables des environnements GitHub.
2. Lancer `Infrastructure` manuellement pour `dev`.
3. Pousser sur `main` pour déclencher `CI`, puis `CD`.
4. Approuver les jobs `staging` et `production` dans GitHub.

Le runner Ubuntu doit pouvoir utiliser Docker. Le workflow `CD` appelle
Terraform, dont le `local-exec` exécute `docker build` et `docker push`.
