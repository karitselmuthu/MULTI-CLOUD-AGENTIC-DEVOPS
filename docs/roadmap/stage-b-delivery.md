# Stage B local delivery slice (weeks 7–10)

Status: mock end-to-end path; no repository, registry, cluster, or cloud mutation.

After signed plan approval and the existing OPA `mock.execute` authorization, Temporal now runs a separate delivery activity. That activity creates a deterministic sample FastAPI source, calculates a content digest, simulates a branch and pull request, runs a syntax gate and four marker-based mock security scanners, checks local mock provenance admission, and simulates GitOps health or rollback. Its report is stored in Temporal workflow state and available at `GET /workflows/{id}/report`. A blocking mock finding or failed mock admission prevents deployment. The report's `mock://` URL makes its simulation status explicit.

The four scanner names (`semgrep-mock`, `trivy-mock`, `checkov-mock`, `gitleaks-mock`) are test doubles. They do not execute Semgrep, Trivy, Checkov, or gitleaks. `to_sarif` emits a SARIF 2.1.0 structure for local evidence. It has not been uploaded to GitHub code scanning, and the adapter does not yet include stable file locations or fingerprints needed for production alert tracking. [GitHub SARIF requirements](https://docs.github.com/en/code-security/reference/code-scanning/sarif-files/sarif-support).

`deployments/helm/fastapi-service` contains a minimal chart with a constrained values schema, digest-pinned image, health probes, resource limits, and a restrictive pod security context. The default image points to `example.invalid` to prevent accidental deployment. `deployments/argocd/fastapi-service-sandbox.yaml` is a manual-sync Argo CD Application example. No EKS/AKS cluster, private registry connection, GitOps controller, or image has been provisioned. References: [Helm charts](https://helm.sh/docs/topics/charts/), [Argo CD Application spec](https://argo-cd.readthedocs.io/en/stable/user-guide/application-specification/).

Local verification:

```text
OPA_BIN=/tmp/opa_darwin_arm64 TEST_DATABASE_URL=<local PostgreSQL DSN> uv run --locked --extra test python -m pytest -q tests
25 passed
helm lint deployments/helm/fastapi-service
1 chart linted, 0 failed (Helm 4.3.1)
helm template sample deployments/helm/fastapi-service --namespace sandbox
rendered Deployment and Service (Helm 4.3.1)
```

Next for a live Stage B exit: authentic GitHub/Azure DevOps adapters, trusted code generation and CI status, actual scanner binaries and SARIF upload, approved Terraform execution, EKS/AKS clusters, image build and signing, and observed GitOps rollout and rollback.
