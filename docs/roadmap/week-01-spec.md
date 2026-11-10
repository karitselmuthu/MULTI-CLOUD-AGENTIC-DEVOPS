# Week 1: request intake and audit foundation

Status: implementation slice 1. Roadmap source: Enterprise Multi-Cloud Agentic DevOps Roadmap v2.0, pages 2 and 5.

## Scope

- Validate AWS and Azure intake requests with an explicit application, infrastructure target, environment, requester and approval intent.
- Persist one workflow ID and `request.received` audit event per accepted request.
- Require an `Idempotency-Key`; return the original workflow for an exact duplicate and HTTP 409 for a changed payload.
- Serve `/health`, `/requests`, and `/workflows/{id}`.
- Keep all requests in `received` state. This slice does not plan, approve, provision or deploy.

## Boundaries

`approval.required=true` only records the need for approval. It is never proof of authorization. No endpoint calls a cloud API or executes Terraform. The requester is self asserted until identity integration is added. Do not expose this API to untrusted networks.

## Exit checks

- AWS and Azure request acceptance and retrieval.
- Invalid cloud, disabled approval, missing idempotency key and duplicate key conflict rejected.
- One audit event for an accepted request; no duplicate event for a replay.
- PostgreSQL-backed records survive API process restart when the same database is used.

## Next slice

Week 2 adds Temporal workflows, mock planning and execution activities, worker restart recovery, approval signals and state transitions. The Phase 1 exit gate remains open until those tests pass.
