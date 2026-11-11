# Cloud sandbox architecture standard (local draft)

For this repository's local acceptance flow, network and registry resources must be created from the reviewed AWS or Azure module paths. AWS test plans use a subnet with automatic public IP assignment disabled. Azure test plans use a registry with public network access disabled. Resource tags identify the owner, cost center and sandbox environment. Unsupported cloud capabilities return explicit errors through the module catalog.

This document is a local fixture for retrieval and review. It is not an organization-approved production standard. A connected rollout must obtain the platform and security owners' approval, confirm cloud-account policy, and validate the exact saved Terraform plan before apply.
