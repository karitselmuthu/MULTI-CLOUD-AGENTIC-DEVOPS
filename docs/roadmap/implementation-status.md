# Roadmap implementation status

This table measures **local code and mock acceptance**, not production readiness. The user selected local mocks for cloud accounts and enterprise systems. No AWS, Azure, TACOS, ITSM, Backstage, or Kubernetes test instance is connected.

| Week | Roadmap item | Local evidence | Remaining live gate |
| --- | --- | --- | --- |
| 1 | Foundation | FastAPI, PostgreSQL intake, audit rows, contracts | Authenticated enterprise access |
| 2 | Temporal | Durable mock workflow, retries, cancellation, recovery tests | Multi-worker and production Temporal validation |
| 3 | Agents | LangGraph planner, structured output, golden cases | Real model gateway and broader model evaluation |
| 4 | Security | HMAC tokens, OPA mock tool gate, approval binding | Enterprise issuer, network MCP service |
| 5 | AWS infrastructure | VPC, private subnet, ECR module validates | AWS account, actual plan, policy, apply |
| 6 | Azure infrastructure | Resource group, VNet, subnet, ACR module validates | Azure subscription, actual plan, policy, apply |
| 7 | Repository automation | Memory-only branch/PR contract and source digest | GitHub/Azure DevOps write adapter and CI status |
| 8 | Security automation | Four marker scanners and SARIF shape | Real Semgrep, Trivy, Checkov, gitleaks and upload |
| 9 | Deployment | Helm chart lints/renders; Argo CD spec; mock GitOps | EKS/AKS, private registry, real rollout and rollback |
| 10 | End-to-end MVP | Approved Temporal mock path and report | Live request-to-deployment acceptance |
| 11 | TACOS | In-memory run, locking, budget and drift checks | HCP Terraform/Spacelift/env0 adapter and remote state |
| 12 | Advanced identity | Five-minute tenant-scoped mock workload token | Cloud workload identity, secret broker and tenant auth |
| 13 | Supply chain | HMAC mock provenance gate before mock rollout | Syft SBOM, cosign, provenance and cluster admission |
| 14 | Agent evaluation | Golden and adversarial mock tests | Measured plan/tool accuracy and model regression gate |
| 15 | Observability | In-memory trace/incident contract | OTel export, Langfuse, dashboards and alerts |
| 16 | Resilience | Mock canary rollback and evidence digest | Live failure recovery, DR and blast-radius exercise |
| 17 | ITSM | In-memory change, plan hash and CAB evidence | ServiceNow/Jira callback and authenticated approval |
| 18 | Developer portal | Backstage catalog and request template examples | Running portal, authenticated request and status UI |
| 19 | Multi-tenant operations | Namespace/budget policy registry and TACOS tenant checks | Real namespaces, quotas, policy bundles and Day-2 controls |
| 20 | Release validation | AWS/Azure local mock acceptance tests | Live cross-cloud, performance, security and DR sign-off |

The highest-risk boundary is the **exact Terraform plan**: the current Stage A planner digest covers a mock proposal, while the Terraform policy tests use synthetic JSON. Before any cloud apply, a trusted executor must generate a binary plan, derive and persist its digest, evaluate its JSON against policy, bind that exact digest to a separate approver's decision, and apply only the saved binary plan. The current mocks deliberately do not implement that live path.

Local checks: `uv run --locked --extra test python -m pytest -q tests`, `opa test security/opa infrastructure/policies -v`, `terraform fmt -check -recursive infrastructure`, `terraform validate` for each initialized module, and `helm lint`/`helm template` for the chart. See [Stage A verification](stage-a-verification.md), [Stage B infrastructure](stage-b-infrastructure.md), and [Stage B delivery](stage-b-delivery.md).
