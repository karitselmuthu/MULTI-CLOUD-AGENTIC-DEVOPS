# Azure sandbox module reference (local fixture)

This module declares a resource group, virtual network, subnet, and Basic Azure Container Registry. Registry admin access and public network access are disabled. Inputs are `name`, `location`, `vnet_cidr`, `subnet_cidr`, and tags. See `variables.tf` for exact validation rules. The module does not create private endpoints, AKS, or workload identities and has not been applied in an Azure subscription.

The local plan gate in `infrastructure/policies/sandbox_plan.rego` accepts only approved resource types, requires owner, cost center and sandbox tags where supported, rejects deletes and public registries, and binds the plan SHA-256 to an approval value. The policy is tested against synthetic plans; no trusted executor applies saved plans yet.
