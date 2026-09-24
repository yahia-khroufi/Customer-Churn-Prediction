## COMMANDS Utilisation

```powershell
cd deploy\terraform
Copy-Item terraform.tfvars.example terraform.tfvars
terraform init
terraform fmt -check
terraform validate
terraform plan -out main.tfplan
terraform apply main.tfplan
```

Par défaut, `terraform apply` utilise Docker local pour construire l'image,
la pousse dans l'ACR, puis crée ou met à jour la Container App. Le terminal
utilisé doit donc disposer de Docker et être authentifié avec Azure CLI :

```powershell
az login
az account set --subscription <subscription-id>
```

Docker Desktop doit également être démarré.

Pour utiliser une image déjà publiée sans la reconstruire :

```hcl
build_image     = false
container_image = "churnyahia2026.azurecr.io/customer-churn:latest"
```
