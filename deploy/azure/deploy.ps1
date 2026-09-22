[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$SubscriptionId,
    [Parameter(Mandatory=$true)][ValidatePattern('^[a-z0-9]{5,50}$')][string]$RegistryName,
    [string]$ResourceGroup = 'rg-customer-churn',
    [string]$Location = 'westeurope',
    [string]$AppName = 'customer-churn',
    [string]$EnvironmentName = 'env-customer-churn',
    [string]$ImageTag = (Get-Date -Format 'yyyyMMddHHmmss')
)

$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    throw 'Installer Azure CLI, ouvrir un nouveau terminal, puis exécuter az login.'
}
foreach ($artifact in @('models\churn_pipeline.joblib', 'models\churn_pipeline.json')) {
    if (-not (Test-Path -LiteralPath (Join-Path $projectRoot $artifact))) {
        throw "Fichier absent : $artifact. Exécuter python run_pipeline.py --evaluate."
    }
}

function Invoke-Azure {
    param([string[]]$Arguments)
    $output = & az @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Échec de az $($Arguments -join ' ')" }
    return $output
}

Invoke-Azure -Arguments @('account', 'set', '--subscription', $SubscriptionId) | Out-Null
Invoke-Azure -Arguments @('account', 'show', '--output', 'table')
Invoke-Azure -Arguments @('extension', 'add', '--name', 'containerapp', '--upgrade', '--only-show-errors') | Out-Null
foreach ($provider in @('Microsoft.App', 'Microsoft.OperationalInsights', 'Microsoft.ContainerRegistry', 'Microsoft.ManagedIdentity')) {
    Invoke-Azure -Arguments @('provider', 'register', '--namespace', $provider, '--wait', '--only-show-errors') | Out-Null
}
Invoke-Azure -Arguments @('group', 'create', '--name', $ResourceGroup, '--location', $Location, '--output', 'none')
$registry = Invoke-Azure -Arguments @(
    'acr', 'create', '--resource-group', $ResourceGroup, '--name', $RegistryName,
    '--location', $Location, '--sku', 'Basic', '--admin-enabled', 'false',
    '--role-assignment-mode', 'rbac', '--output', 'json'
) | ConvertFrom-Json
Invoke-Azure -Arguments @('acr', 'config', 'authentication-as-arm', 'update', '-r', $RegistryName, '--status', 'enabled', '--output', 'none')

# Construction dans Azure : aucun moteur Docker local n'est nécessaire.
Invoke-Azure -Arguments @(
    'acr', 'build', '--registry', $RegistryName, '--image', "customer-churn:$ImageTag",
    '--platform', 'linux/amd64', '--file', 'Dockerfile', $projectRoot
)
$identity = Invoke-Azure -Arguments @(
    'identity', 'create', '--name', "$AppName-pull", '--resource-group', $ResourceGroup,
    '--location', $Location, '--output', 'json'
) | ConvertFrom-Json
$roles = Invoke-Azure -Arguments @(
    'role', 'assignment', 'list', '--assignee', $identity.principalId,
    '--scope', $registry.id, '--role', 'AcrPull', '--output', 'json'
) | ConvertFrom-Json
if (@($roles).Count -eq 0) {
    Invoke-Azure -Arguments @(
        'role', 'assignment', 'create', '--assignee-object-id', $identity.principalId,
        '--assignee-principal-type', 'ServicePrincipal', '--scope', $registry.id,
        '--role', 'AcrPull', '--output', 'none'
    )
}
$environment = Invoke-Azure -Arguments @(
    'containerapp', 'env', 'create', '--name', $EnvironmentName,
    '--resource-group', $ResourceGroup, '--location', $Location, '--output', 'json'
) | ConvertFrom-Json

# JSON est aussi un document YAML valide. Les probes HTTP contrôlent le vrai modèle.
$definition = @{
    location = $Location
    identity = @{ type = 'UserAssigned'; userAssignedIdentities = @{ ($identity.id) = @{} } }
    properties = @{
        managedEnvironmentId = $environment.id
        configuration = @{
            activeRevisionsMode = 'Single'
            ingress = @{ external = $true; targetPort = 8000; transport = 'auto'; allowInsecure = $false }
            registries = @(@{ server = $registry.loginServer; identity = $identity.id })
        }
        template = @{
            containers = @(@{
                name = 'churn-app'
                image = "$($registry.loginServer)/customer-churn:$ImageTag"
                resources = @{ cpu = 0.5; memory = '1Gi' }
                env = @(@{ name = 'MODEL_PATH'; value = '/app/models/churn_pipeline.joblib' })
                probes = @(
                    @{ type = 'Startup'; httpGet = @{ path = '/health'; port = 8000 }; periodSeconds = 5; timeoutSeconds = 3; failureThreshold = 30 },
                    @{ type = 'Readiness'; httpGet = @{ path = '/health'; port = 8000 }; periodSeconds = 10; timeoutSeconds = 3; failureThreshold = 3 },
                    @{ type = 'Liveness'; httpGet = @{ path = '/'; port = 8000 }; periodSeconds = 30; timeoutSeconds = 3; failureThreshold = 3 }
                )
            })
            scale = @{
                minReplicas = 0; maxReplicas = 1
                rules = @(@{ name = 'http-requests'; http = @{ metadata = @{ concurrentRequests = '10' } } })
            }
        }
    }
}
$configFile = Join-Path ([System.IO.Path]::GetTempPath()) ("churn-azure-" + [guid]::NewGuid().ToString('N') + '.json')
try {
    $definition | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $configFile -Encoding UTF8
    Invoke-Azure -Arguments @(
        'containerapp', 'create', '--name', $AppName, '--resource-group', $ResourceGroup,
        '--yaml', $configFile, '--output', 'none'
    )
} finally {
    if (Test-Path -LiteralPath $configFile) { Remove-Item -LiteralPath $configFile }
}
$fqdn = Invoke-Azure -Arguments @(
    'containerapp', 'show', '--name', $AppName, '--resource-group', $ResourceGroup,
    '--query', 'properties.configuration.ingress.fqdn', '--output', 'tsv'
)
Write-Host "Interface : https://$fqdn"
Write-Host "API       : https://$fqdn/docs"
Write-Host "Santé     : https://$fqdn/health"
Write-Host 'Vérifier /health puis faire une prédiction avec un exemple fictif.'
