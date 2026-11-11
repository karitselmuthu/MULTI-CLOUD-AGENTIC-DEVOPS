# Stage B infrastructure slice (weeks 5–6)

Status: locally validated module scaffold; no cloud resources created.

The AWS and Azure modules each define one isolated network, one private subnet, and one container registry. Their outputs use common names (`network_id`, `private_subnet_id`, `registry_url`). Input tags require `owner`, `cost_center`, and `environment=sandbox`. The AWS repository uses immutable tags and scan-on-push; Azure ACR disables admin access and public network access.

The sandbox plan policy at `infrastructure/policies/sandbox_plan.rego` is deny by default. It accepts only the seven resource types used by these modules, sandbox environment, a matching SHA-256 approval digest, required tags, and no delete or public exposure. This policy is currently a **local prototype** tested against synthetic Terraform JSON. Its `approval.valid` field is test data, not a trusted verification result. It must be integrated with a real plan producer and the signed approval service before a Terraform executor can trust it. In particular, a plan must be hashed from the exact binary plan that will be applied, and the executor must reject a changed plan after approval.

The AWS sandbox root now provides an explicit AWS account guard, region, module inputs, and partial S3 backend configuration with a documented locking setup. A CloudFormation template for a private, versioned state bucket is prepared but not deployed. The root and template validate locally; no AWS plan or apply has run. The selected profile authenticated as the account root principal. That session was logged out, and live operations require a non-root role. A live run still requires that role, an approved state bucket and CIDRs, and exact saved-plan approval. The Azure root remains a future connected step. EKS/AKS and private registry connectivity are later Stage B work; these modules alone do not deploy applications. Azure ACR's disabled public endpoint will require private connectivity before image pushes are possible. See the [AWS sandbox root guide](../../infrastructure/environments/aws-sandbox/README.md) and [state bucket bootstrap](../../infrastructure/environments/aws-state-bootstrap/README.md).

Verification completed locally with Terraform 1.15.6, AWS provider 6.72.0, AzureRM provider 5.13.0, and OPA 1.22.2:

```text
terraform fmt -check -recursive infrastructure          PASS
terraform validate -no-color (AWS module)                PASS
terraform validate -no-color (Azure module)              PASS
opa test infrastructure/policies -v                      10/10 PASS
```

Terraform validation checks configuration syntax and provider schemas, not cloud behavior or a real plan. References: [Terraform validate](https://developer.hashicorp.com/terraform/cli/commands/validate), [module structure](https://developer.hashicorp.com/terraform/language/modules/develop/structure), [plan JSON](https://developer.hashicorp.com/terraform/internals/json-format), [OPA policy language](https://www.openpolicyagent.org/docs/policy-language).
