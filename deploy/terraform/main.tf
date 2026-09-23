locals {
  image = var.container_image != "" ? var.container_image : "${azurerm_container_registry.main.login_server}/customer-churn:${var.image_tag}"
}

resource "azurerm_resource_group" "main" {
  name     = var.resource_group_name
  location = var.location
  tags     = var.tags
}

resource "azurerm_container_registry" "main" {
  name                = var.registry_name
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "Basic"
  admin_enabled       = false
  tags                = var.tags
}

resource "azurerm_log_analytics_workspace" "main" {
  name                = "${var.app_name}-logs"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = var.tags
}

resource "azurerm_container_app_environment" "main" {
  name                       = var.environment_name
  resource_group_name        = azurerm_resource_group.main.name
  location                   = azurerm_resource_group.main.location
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id
  tags                       = var.tags
}

resource "azurerm_user_assigned_identity" "pull" {
  name                = var.identity_name
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  tags                = var.tags
}

resource "azurerm_role_assignment" "acr_pull" {
  scope                = azurerm_container_registry.main.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.pull.principal_id
}

resource "azurerm_container_app" "main" {
  name                         = var.app_name
  resource_group_name          = azurerm_resource_group.main.name
  container_app_environment_id = azurerm_container_app_environment.main.id
  revision_mode                = "Single"
  tags                         = var.tags

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.pull.id]
  }

  registry {
    server   = azurerm_container_registry.main.login_server
    identity = azurerm_user_assigned_identity.pull.id
  }

  dynamic "secret" {
    for_each = var.app_secrets
    content {
      name  = secret.key
      value = secret.value
    }
  }

  ingress {
    external_enabled = true
    target_port      = 8000
    transport        = "auto"

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  template {
    min_replicas = var.min_replicas
    max_replicas = var.max_replicas

    container {
      name   = "churn-app"
      image  = local.image
      cpu    = var.container_cpu
      memory = var.container_memory

      dynamic "env" {
        for_each = {
          for name, value in var.app_environment_variables : name => value
          if !contains(keys(var.secret_environment_variables), name)
        }
        content {
          name  = env.key
          value = env.value
        }
      }

      dynamic "env" {
        for_each = var.secret_environment_variables
        content {
          name        = env.key
          secret_name = env.value
        }
      }

      startup_probe {
        transport     = "HTTP"
        port          = 8000
        path          = "/health"
        interval_seconds = 5
        timeout         = 3
        failure_count   = 30
      }

      readiness_probe {
        transport        = "HTTP"
        port              = 8000
        path              = "/health"
        interval_seconds  = 10
        timeout            = 3
        failure_count      = 3
      }

      liveness_probe {
        transport        = "HTTP"
        port              = 8000
        path              = "/"
        interval_seconds  = 30
        timeout            = 3
        failure_count      = 3
      }
    }

    http_scale_rule {
      name                = "http-requests"
      concurrent_requests = 10
    }
  }
}
