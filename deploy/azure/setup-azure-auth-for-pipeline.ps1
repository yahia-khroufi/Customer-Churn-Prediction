[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Owner,
    [Parameter(Mandatory = $true)][string]$Repository,
    [Parameter(Mandatory = $true)][string]$RegistryName,
    [string]$SubscriptionId = '35726a57-2e04-4b2d-afb2-d8373578a5db',
    [string]$Location = 'germanywestcentral',
    [string]$PipelineResourceGroup = 'rg-customer-churn-github',
    [string]$IdentityName = 'id-customer-churn-github',
    [string]$ApplicationResourceGroup = 'rg-customer-churn'
)

$ErrorActionPreference = 'Stop'

az account set --subscription $SubscriptionId
az group create --name $PipelineResourceGroup --location $Location --output none
az identity create --name $IdentityName --resource-group $PipelineResourceGroup --location $Location --output none

$identity = az identity show --name $IdentityName --resource-group $PipelineResourceGroup | ConvertFrom-Json
$scope = az group show --name $ApplicationResourceGroup --query id --output tsv

az role assignment create `
    --assignee-object-id $identity.principalId `
    --assignee-principal-type ServicePrincipal `
    --role Contributor `
    --scope $scope `
    --output none

$registryScope = az acr show --name $RegistryName --resource-group $ApplicationResourceGroup --query id --output tsv
az role assignment create `
    --assignee-object-id $identity.principalId `
    --assignee-principal-type ServicePrincipal `
    --role AcrPush `
    --scope $registryScope `
    --output none

foreach ($environment in @('dev', 'staging', 'production')) {
    az identity federated-credential create `
        --name "github-$environment" `
        --identity-name $IdentityName `
        --resource-group $PipelineResourceGroup `
        --issuer 'https://token.actions.githubusercontent.com' `
        --subject "repo:$Owner/$Repository`:environment:$environment" `
        --audiences 'api://AzureADTokenExchange' `
        --output none
}

Write-Host "AZURE_CLIENT_ID=$($identity.clientId)"
Write-Host "AZURE_TENANT_ID=$(az account show --query tenantId --output tsv)"
Write-Host 'Configure these values as GitHub Environment variables for dev, staging, and production.'
