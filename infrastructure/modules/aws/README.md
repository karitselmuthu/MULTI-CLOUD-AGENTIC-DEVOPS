# AWS sandbox module reference (local fixture)

This module currently declares an AWS VPC with DNS support, one subnet with public IP assignment disabled, and an immutable encrypted ECR repository with scan-on-push enabled. Inputs are `name`, `vpc_cidr`, `subnet_cidr`, `availability_zone`, and required tags. See `variables.tf` for exact validation rules. The module does not create routes, NAT, EKS, or IAM roles and has not been applied in an AWS account.

The local plan gate in `infrastructure/policies/sandbox_plan.rego` accepts only approved resource types, requires owner, cost center and sandbox tags, rejects deletes and public subnets, and binds the plan SHA-256 to an approval value. The policy is tested against synthetic plans; no trusted executor applies saved plans yet.
