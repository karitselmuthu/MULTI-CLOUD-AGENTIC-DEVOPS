# MULTI-CLOUD-AGENTIC-DEVOPS

Production-oriented Agentic DevOps platform for governed infrastructure and application delivery across AWS and Azure.

## Current state

Week 1 intake foundation: validated requests, persistent workflow records and audit metadata. All workflows remain `received`; no cloud mutation is implemented.

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
