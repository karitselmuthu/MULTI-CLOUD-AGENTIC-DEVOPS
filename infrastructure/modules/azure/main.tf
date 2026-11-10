# Provider resource schemas: https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/resource_group
resource "azurerm_resource_group" "sandbox" {
  name     = "${var.name}-rg"
  location = var.location
  tags     = var.tags
}

# https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/virtual_network
resource "azurerm_virtual_network" "sandbox" {
  name                = "${var.name}-vnet"
  location            = azurerm_resource_group.sandbox.location
  resource_group_name = azurerm_resource_group.sandbox.name
  address_space       = [var.vnet_cidr]
  tags                = var.tags
}

# https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/subnet
resource "azurerm_subnet" "private" {
  name                 = "${var.name}-private"
  resource_group_name  = azurerm_resource_group.sandbox.name
  virtual_network_name = azurerm_virtual_network.sandbox.name
  address_prefixes     = [var.subnet_cidr]
}

# https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/container_registry
resource "azurerm_container_registry" "images" {
  name                          = "${var.name}registry"
  resource_group_name           = azurerm_resource_group.sandbox.name
  location                      = azurerm_resource_group.sandbox.location
  sku                           = "Basic"
  admin_enabled                 = false
  public_network_access_enabled = false
  tags                          = var.tags
}
