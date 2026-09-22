# Déploiement Azure : tâches à réaliser dans ton compte

Le dépôt contient tout ce qui est nécessaire pour construire l'image et lancer
l'interface + FastAPI sur **Azure Container Apps**, avec l'image privée dans
**Azure Container Registry**. Le script ne déploie pas le serveur MLflow : le suivi
des expériences reste local, indépendant du service de prédiction.

## 1. Préparer ton compte

1. Créer ou choisir un abonnement Azure actif.
2. Dans **Cost Management > Budgets**, définir un budget et une alerte. Une alerte
   ne coupe pas automatiquement les ressources. ACR et les logs peuvent coûter
   même lorsque l'application est réduite à zéro réplique.
3. Disposer des droits de création de ressources et d'attribution de rôles :
   **Owner**, ou **Contributor + Role Based Access Control Administrator** au scope
   approprié. Le rôle `AcrPull` sera donné à l'identité de l'application.
4. Installer [Azure CLI sous Windows](https://learn.microsoft.com/cli/azure/install-azure-cli-windows),
   puis ouvrir un nouveau terminal.

```powershell
az login
az account list --output table
```

Choisir l'ID de l'abonnement et un nom de registre **globalement unique**, composé
de 5 à 50 lettres minuscules et chiffres, par exemple `churnmonnom2026`.

## 2. Vérifier le modèle et les tests

Depuis la racine du projet, avec le `.venv` actif :

```powershell
python -m pytest tests/ -q
python -m src.models.predict examples/customer.json
```

Les fichiers `models/churn_pipeline.joblib` et `models/churn_pipeline.json` doivent
être présents. Sur une nouvelle copie du dépôt, les recréer avec :

```powershell
python run_pipeline.py --evaluate --track
```

L'image ne contient ni le dataset brut ni les notebooks. Le pipeline et le rapport
du modèle sont copiés dans l'image au moment de la construction.

## 3. Créer les ressources et déployer

Cette commande crée des ressources facturables dans l'abonnement indiqué :

```powershell
.\deploy\azure\deploy.ps1 `
  -SubscriptionId "TON-ID-ABONNEMENT" `
  -RegistryName "churnmonnom2026" `
  -Location "westeurope"
```

Le script crée le groupe `rg-customer-churn`, le registre ACR Basic, une identité
managée avec `AcrPull`, un environnement Container Apps et l'application
`customer-churn`. Il construit l'image dans ACR ; Docker local n'est donc pas
nécessaire pour ce déploiement. Il utilise un tag horodaté et affiche l'URL HTTPS.

L'application démarre avec 0,5 CPU / 1 Gio et passe de zéro à une réplique selon
les requêtes. Le premier accès peut être plus lent après une période d'inactivité.
La sonde de disponibilité vérifie `/health`, donc le chargement du pipeline.

## 4. Vérifier dans le portail Azure

1. **Resource groups > rg-customer-churn** : vérifier les ressources créées.
2. **Container Registry > Repositories** : retrouver `customer-churn` et son tag.
3. **Container Apps > customer-churn > Overview** : ouvrir l'URL de l'application.
4. Ouvrir `/health` : réponse HTTP 200, `model_loaded: true`.
5. Tester « Nouveau client » et « Client fidèle » dans l'interface.
6. Dans **Log stream**, vérifier le démarrage. Les **Revisions** doivent être saines.

```powershell
az containerapp logs show --name customer-churn --resource-group rg-customer-churn --follow
```

Si le téléchargement de l'image échoue, vérifier l'attribution `AcrPull`, attendre
la propagation du rôle puis relancer le script. Un abonnement étudiant peut aussi
avoir des restrictions de quota ou d'accès aux builds ACR : consulter le message
Azure avant de modifier le type de ressources.

## 5. Démo et utilisation réelle

L'URL déployée est une **démo publique sans authentification**. Utiliser des profils
fictifs. Pour un usage interne avec de vraies données clients, activer une
authentification Microsoft Entra ID dans **Authentication** et restreindre l'accès,
puis définir les règles de conservation, supervision et validation métier.
MLflow doit rester privé. Pour le partager durablement, prévoir un serveur de suivi
authentifié, une base de données persistante et un stockage d'artefacts Azure Blob.

## 6. Mettre à jour ou arrêter

Après modification du code ou du pipeline, relancer le script avec les mêmes noms.
Un nouveau tag d'image crée une nouvelle révision. Vérifier `/health` et les exemples.

Pour arrêter tous les coûts du projet de démonstration, supprimer **uniquement le
groupe dédié** depuis le portail, après avoir vérifié son contenu. Cette opération
supprime les ressources cloud qu'il contient, pas tes fichiers locaux.

## Sources officielles

- [Images ACR avec identité managée](https://learn.microsoft.com/azure/container-apps/managed-identity-image-pull)
- [Construction distante avec ACR Tasks](https://learn.microsoft.com/azure/container-registry/container-registry-quickstart-task-cli)
- [Commandes Container Apps](https://learn.microsoft.com/cli/azure/containerapp)
