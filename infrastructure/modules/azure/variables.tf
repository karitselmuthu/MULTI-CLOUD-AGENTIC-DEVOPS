variable "name" {
  description = "Unique lowercase sandbox resource prefix."
  type        = string
  validation {
    condition     = can(regex("^[a-z][a-z0-9]{4,19}$", var.name))
    error_message = "Use 5-20 lowercase letters or digits, starting with a letter."
  }
}

variable "location" {
  description = "Azure region chosen by the sandbox owner."
  type        = string
}

variable "vnet_cidr" {
  description = "IPv4 CIDR for the sandbox virtual network."
  type        = string
  validation {
    condition     = can(cidrhost(var.vnet_cidr, 0))
    error_message = "Provide a valid IPv4 CIDR."
  }
}

variable "subnet_cidr" {
  description = "Private subnet CIDR contained within vnet_cidr."
  type        = string
  validation {
    condition     = can(cidrhost(var.subnet_cidr, 0))
    error_message = "Provide a valid IPv4 CIDR."
  }
}

variable "tags" {
  description = "Required ownership and cost allocation tags."
  type        = map(string)
  validation {
    condition     = alltrue([for key in ["owner", "cost_center", "environment"] : length(trimspace(lookup(var.tags, key, ""))) > 0]) && lookup(var.tags, "environment", "") == "sandbox"
    error_message = "owner, cost_center, and environment=sandbox tags are required."
  }
}
