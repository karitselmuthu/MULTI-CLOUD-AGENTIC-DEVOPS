output "network_id" {
  description = "Sandbox virtual network identifier."
  value       = azurerm_virtual_network.sandbox.id
}

output "private_subnet_id" {
  description = "Private subnet identifier."
  value       = azurerm_subnet.private.id
}

output "registry_url" {
  description = "Private image registry endpoint."
  value       = azurerm_container_registry.images.login_server
}
