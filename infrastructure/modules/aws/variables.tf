variable "name" {
  description = "Unique sandbox resource prefix."
  type        = string
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,30}$", var.name))
    error_message = "Use 3-31 lowercase letters, digits, or hyphens, starting with a letter."
  }
}

variable "vpc_cidr" {
  description = "IPv4 CIDR for the sandbox VPC."
  type        = string
  validation {
    condition     = can(cidrhost(var.vpc_cidr, 0))
    error_message = "Provide a valid IPv4 CIDR."
  }
}

variable "subnet_cidr" {
  description = "Private subnet CIDR contained within vpc_cidr."
  type        = string
  validation {
    condition     = can(cidrhost(var.subnet_cidr, 0))
    error_message = "Provide a valid IPv4 CIDR."
  }
}

variable "availability_zone" {
  description = "Availability zone for the sandbox subnet."
  type        = string
}

variable "tags" {
  description = "Required ownership and cost allocation tags."
  type        = map(string)
  validation {
    condition     = alltrue([for key in ["owner", "cost_center", "environment"] : length(trimspace(lookup(var.tags, key, ""))) > 0]) && lookup(var.tags, "environment", "") == "sandbox"
    error_message = "owner, cost_center, and environment=sandbox tags are required."
  }
}
