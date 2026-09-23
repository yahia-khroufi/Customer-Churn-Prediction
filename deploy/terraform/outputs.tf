output "resource_group_name" {
  description = "Resource group name."
  value       = azurerm_resource_group.main.name
}

output "registry_login_server" {
  description = "Private ACR login server."
  value       = azurerm_container_registry.main.login_server
}

output "container_app_url" {
  description = "HTTPS URL of the deployed Container App."
  value       = "https://${azurerm_container_app.main.ingress[0].fqdn}"
}

output "container_app_name" {
  description = "Container App name."
  value       = azurerm_container_app.main.name
}

output "managed_identity_principal_id" {
  description = "Principal ID of the image-pull managed identity."
  value       = azurerm_user_assigned_identity.pull.principal_id
}
