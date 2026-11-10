# Test category matrix

This matrix follows the requested categories. **Local** means executable against repository code and mocks. **Live pending** means the scenario requires a connected cloud, enterprise system, or production-like deployment; a passing mock test does not satisfy it.

| Category | Requested key scenarios | Local evidence | Live pending |
| --- | --- | --- | --- |
| Unit | Agent contracts, schema validation, cloud adapters, policy decisions | `tests/unit/test_planning.py`, `test_api.py`, `test_tacos.py`, `test_tenants.py`; OPA tests in `security/opa/` and `infrastructure/policies/` | Provider adapter behavior against real APIs |
| Integration | Temporal, PostgreSQL, MCP gateway, Git provider, Terraform platform | `tests/integration/test_temporal_workflow.py`, `test_postgres.py`, `test_api_workflow.py`, `test_dispatch.py`, `test_api_failures.py`; `tests/security/test_gateway.py`; mock Git/TACOS in cross-cloud e2e | GitHub/Azure DevOps writes, HCP Terraform or equivalent, network MCP service |
| Cloud | AWS and Azure provisioning, IAM, networking, cluster deployment | Terraform AWS/Azure module schema validation and `tests/e2e/test_enterprise_mock_acceptance.py` | Actual sandbox plans/applies, IAM/workload identity, EKS/AKS and networking tests |
| Negative | Invalid request, unauthorized access, expired approval, missing secret | `tests/unit/test_api.py`, `tests/security/test_gateway.py`, `tests/integration/test_api_failures.py` | Enterprise API authentication and authorization; the current local intake/read API is unauthenticated |
| Failure recovery | Worker crash, duplicate events, API timeout, partial provisioning | `tests/integration/test_temporal_workflow.py`, `test_dispatch.py`, `test_api_failures.py`; `tests/unit/test_tacos.py::test_partial_mock_provisioning_compensates_without_spend` | Multi-worker crash recovery and real infrastructure compensation |
| Security | Prompt injection, privilege escalation, secret leakage, policy bypass | `tests/security/test_prompt_injection.py`, `test_gateway.py`; `tests/unit/test_delivery.py`; Rego tests | Real scanner results, tenant identity boundaries, production policy enforcement |
| Supply chain | Unsigned image, vulnerable dependency, invalid SBOM or provenance | `tests/security/test_provenance.py` and `tests/unit/test_delivery.py` use mock SBOM and scanner markers; admission blocks rollout | Syft/CycloneDX or SPDX validation, cosign signatures, registry and cluster admission |
| Evaluation | Plan correctness, tool accuracy, policy compliance, hallucinated resources | Golden requests in `tests/unit/test_planning.py`; `tests/security/test_prompt_injection.py`, `test_gateway.py`; Rego tests | Model-based regression dataset, measured accuracy thresholds and live tool-call evaluation |
| Performance | Concurrent workflows, queue latency, API throughput, recovery time | `tests/performance/test_mock_concurrency.py` stresses 20 concurrent mock applies and budget isolation | Temporal workflow concurrency, queue and API benchmarks, recovery-time SLOs |
| Disaster recovery | Database restoration, workflow recovery, credential revocation | `tests/resilience/test_local_recovery.py` restores a tenant-scoped metadata snapshot; `tests/integration/test_temporal_workflow.py` resumes after worker restart; `tests/unit/test_enterprise_controls.py` revokes an in-process token | PostgreSQL backup/restore, Temporal cluster recovery, distributed credential revocation |

## Continuous checks

The Python GitHub workflow runs every `tests/` file with PostgreSQL and OPA configured. The infrastructure workflow runs Terraform formatting/schema validation, Rego tests, and Helm lint/render. Locally, use `OPA_BIN=<opa path> TEST_DATABASE_URL=<test DSN> uv run --locked --extra test python -m pytest -q tests` and `opa test security/opa infrastructure/policies -v`. See the [milestone acceptance contract](../roadmap/milestone-acceptance.md) for M1–M6 release status.

The mock SBOM has a deliberately narrow `mock-sbom-v1` shape. Its acceptance test does not validate CycloneDX or SPDX. The local revocation list exists within one `TokenVerifier` process and is not durable or distributed. The concurrency test asserts state safety, not a throughput target.
