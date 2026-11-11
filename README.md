# MULTI-CLOUD-AGENTIC-DEVOPS

Production-oriented Agentic DevOps platform for governed infrastructure and application delivery across AWS and Azure.

## Current state

Stage A local foundation: validated requests, persistent workflow records, durable Temporal mock workflows, LangGraph planning, signed approval binding, and an OPA-gated mock tool gateway. Stage B adds locally validated AWS and Azure Terraform sandbox modules, a prototype plan policy, and a mock delivery report. Stages C and D add local mock contracts for TACOS, workload identity, provenance, observability, resilience, ITSM, tenant policy, and a Backstage template. No cloud or external system mutation is implemented. [The roadmap status table](docs/roadmap/implementation-status.md) separates local evidence from live acceptance gates.

The new [knowledge, model gateway and dashboard slice](docs/architecture/knowledge-gateway-dashboard.md) adds Qdrant-filtered local reference retrieval, provider-neutral routing, separate artifact/cache adapters, optional Langfuse and OpenTelemetry observations, retrieval evaluation, and a [React dashboard](apps/dashboard/README.md). These remain local development integrations; the connected enterprise gates are documented in that architecture note.

The [repository integration review](docs/architecture/repository-integration-review.md) maps the newer domain directories to code and names the Backstage, pgvector and distributed-system gates that remain open.
The [frontend acceptance matrix](docs/roadmap/frontend-acceptance.md) tracks FE-01–FE-13 with local browser evidence and the remaining SSO, Backstage, accessibility and load gates.

The [M1–M6 acceptance contract](docs/roadmap/milestone-acceptance.md) maps each requested criterion to executable evidence and names the live gates that remain open.
The [test category matrix](docs/governance/test-matrix.md) tracks unit, integration, cloud, negative, recovery, security, supply chain, evaluation, performance, and disaster recovery coverage.

The repository follows the proposed domain layout. Directories without implemented workstreams contain `.gitkeep` placeholders so Git retains the full structure. The [cloud capability matrix](cloud/capability_matrix.yaml) records planned AWS and Azure mappings; it does not imply active integrations.

## Local setup

Requires Python 3.11+, Docker and a local PostgreSQL service.

```sh
docker compose up -d postgres
uv venv
uv pip install -e '.[test]'
.venv/bin/python -m apps.api.init_db
.venv/bin/uvicorn apps.api.main:app --reload
```

Example request:

```sh
curl -X POST http://localhost:8000/requests \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: demo-001' \
  -d '{"cloud":"aws","environment":"sandbox","requester":"engineer@example.com","application":{"name":"sample-api","repository":"https://github.com/example/sample-api"},"infrastructure":{"region":"us-east-1","module":"sandbox-api"},"approval":{"required":true}}'
```

Run tests with `.venv/bin/pytest`. See [Week 1 specification](docs/roadmap/week-01-spec.md) and [ADR 0001](docs/adr/0001-persistent-intake-before-orchestration.md).

For local development, start a Temporal dev server on `localhost:7233`, set `TEMPORAL_ADDRESS=localhost:7233` for the API, then run `.venv/bin/python -m orchestration.temporal.workers.mock_worker` in a separate terminal. The worker polls `received` rows and starts mock workflows. See [Week 2 specification](docs/roadmap/week-02-spec.md) and [ADR 0002](docs/adr/0002-temporal-dispatch-and-mock-boundary.md).

The planning activity uses an offline LangGraph graph and a mock module catalog. Golden requests and expected plan fields live under `evaluations/`. See [Week 3 specification](docs/roadmap/week-03-spec.md) and [ADR 0003](docs/adr/0003-langgraph-inside-planning-activity.md).

For mock approvals, set a unique 32-byte or longer `AGENT_SIGNING_KEY` in both API and worker processes and install the [OPA CLI](https://www.openpolicyagent.org/docs). The API exposes `POST /workflows/{id}/approve` for signed approval claims; it does not issue claims or authenticate approvers. This interface is for isolated local development only. See [Week 4 specification](docs/roadmap/week-04-spec.md) and [Stage A verification](docs/roadmap/stage-a-verification.md).

After a mock workflow completes, `GET /workflows/{id}/report` returns branch, pull request, CI, security, and deployment simulation evidence. See [Stage B infrastructure](docs/roadmap/stage-b-infrastructure.md) and [Stage B delivery](docs/roadmap/stage-b-delivery.md). The Terraform modules and Helm chart are validated locally only; the plan policy is not connected to a real executor.
