variable "aws_account_id" {
  description = "Approved 12-digit sandbox account ID."
  type        = string
  validation {
    condition     = can(regex("^[0-9]{12}$", var.aws_account_id))
    error_message = "aws_account_id must be a 12-digit account ID."
  }
}

variable "aws_region" {
  description = "Approved AWS Region for this sandbox."
  type        = string
  validation {
    condition     = can(regex("^[a-z]{2}-[a-z-]+-[0-9]$", var.aws_region))
    error_message = "aws_region must be an AWS Region such as us-east-1."
  }
}

variable "name" {
  description = "Unique prefix for the three sandbox resources."
  type        = string
}

variable "vpc_cidr" {
  description = "Sandbox VPC CIDR, approved by the account owner."
  type        = string
}

variable "subnet_cidr" {
  description = "Private subnet CIDR inside vpc_cidr."
  type        = string
}

variable "availability_zone" {
  description = "Availability zone in aws_region."
  type        = string
}

variable "owner" {
  description = "Owner tag value."
  type        = string
}

variable "cost_center" {
  description = "Cost allocation tag value."
  type        = string
}
