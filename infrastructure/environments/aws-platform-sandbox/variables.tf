variable "aws_account_id" {
  type = string
  validation {
    condition     = can(regex("^[0-9]{12}$", var.aws_account_id))
    error_message = "Use the approved 12-digit AWS account ID."
  }
}

variable "aws_region" {
  type = string
}

variable "name" {
  description = "Unique lowercase prefix for sandbox resources."
  type        = string
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,20}$", var.name))
    error_message = "Use 3-21 lowercase letters, digits, or hyphens, starting with a letter."
  }
}

variable "vpc_id" {
  type = string
}

variable "alb_subnet_ids" {
  description = "At least two private subnets in different Availability Zones, routable from the operator network."
  type        = list(string)
  validation {
    condition     = length(distinct(var.alb_subnet_ids)) >= 2
    error_message = "An ALB needs at least two distinct subnets."
  }
}

variable "task_subnet_ids" {
  description = "Private subnets with egress to Temporal Cloud and AWS service endpoints."
  type        = list(string)
  validation {
    condition     = length(var.task_subnet_ids) >= 1
    error_message = "Provide at least one private task subnet."
  }
}

variable "allowed_ingress_cidrs" {
  description = "Approved internal operator network CIDRs for the HTTPS ALB."
  type        = list(string)
  validation {
    condition = length(var.allowed_ingress_cidrs) > 0 && alltrue([
      for cidr in var.allowed_ingress_cidrs :
      can(cidrhost(cidr, 0)) && cidr != "0.0.0.0/0"
    ])
    error_message = "Provide specific internal CIDRs; public internet access is forbidden."
  }
}

variable "tls_certificate_arn" {
  description = "ACM certificate in aws_region for the internal API DNS name."
  type        = string
}

variable "image_uri" {
  description = "ECR image reference pinned to a sha256 digest."
  type        = string
  validation {
    condition     = can(regex("^[0-9]{12}\\.dkr\\.ecr\\.[a-z0-9-]+\\.amazonaws\\.com/.+@sha256:[0-9a-f]{64}$", var.image_uri))
    error_message = "Pin an ECR image by sha256 digest."
  }
}

variable "ecr_repository_arn" {
  description = "Repository holding image_uri."
  type        = string
}

variable "database_url_secret_arn" {
  description = "Secrets Manager ARN containing a complete PostgreSQL connection URL."
  type        = string
}

variable "temporal_api_key_secret_arn" {
  type = string
}

variable "signing_key_secret_arn" {
  type = string
}

variable "dashboard_token_secret_arn" {
  type = string
}

variable "temporal_address" {
  description = "Temporal Cloud namespace endpoint, host:7233."
  type        = string
  validation {
    condition     = can(regex("^[A-Za-z0-9.-]+:7233$", var.temporal_address))
    error_message = "Use a Temporal Cloud host on port 7233."
  }
}

variable "temporal_namespace" {
  type = string
}

variable "dashboard_requester" {
  description = "Single approved sandbox operator email."
  type        = string
}

variable "owner" {
  type = string
}

variable "cost_center" {
  type = string
}

variable "api_desired_count" {
  description = "Keep at zero until the migration task succeeds."
  type        = number
  default     = 0
  validation {
    condition     = var.api_desired_count >= 0 && var.api_desired_count <= 2
    error_message = "Sandbox API task count must be between zero and two."
  }
}

variable "worker_desired_count" {
  description = "Keep at zero until the migration task succeeds."
  type        = number
  default     = 0
  validation {
    condition     = var.worker_desired_count >= 0 && var.worker_desired_count <= 1
    error_message = "Sandbox worker task count must be zero or one."
  }
}
