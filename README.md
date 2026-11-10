# MULTI-CLOUD-AGENTIC-DEVOPS

Production-oriented Agentic DevOps platform for governed infrastructure and application delivery across AWS and Azure.

## Current state

Week 1 intake foundation and a Week 2 Temporal mock orchestration slice: validated requests, persistent workflow records, audit metadata, and a worker that dispatches accepted requests to durable mock workflows. No cloud mutation is implemented.

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

For Week 2 development, start a Temporal dev server on `localhost:7233`, then run `.venv/bin/python -m orchestration.temporal.workers.mock_worker` in a separate terminal. The worker polls `received` rows and starts mock workflows. Approval signals are available through the Temporal SDK for integration testing; no user approval endpoint is exposed yet. See [Week 2 specification](docs/roadmap/week-02-spec.md) and [ADR 0002](docs/adr/0002-temporal-dispatch-and-mock-boundary.md).
