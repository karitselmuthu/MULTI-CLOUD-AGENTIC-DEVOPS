# Security policy reference (local draft)

The mock tool gateway denies by default. The planning agent can read the catalog for its workflow; the DevOps agent can call `mock.execute` only with a matching workflow and valid plan-bound approval outside production. The sandbox Terraform plan policy blocks missing approval, digest mismatch, deletes, unapproved resources, public AWS subnets, public Azure registries, and missing required tags.

These rules are executable in `security/opa/tools.rego` and `infrastructure/policies/sandbox_plan.rego`. They are local prototypes; there is no cloud executor or organization-approved policy bundle connected yet.
