terraform {
  required_version = ">= 1.15.0, < 2.0.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }

  # Supply bucket, key, region, and use_lockfile=true at terraform init.
  # https://developer.hashicorp.com/terraform/language/backend/s3
  backend "s3" {}
}
