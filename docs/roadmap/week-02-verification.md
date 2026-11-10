# Week 2 verification

Date: 2026-11-10 (Asia/Kolkata)

- Temporal Python SDK: 1.35.0.
- `pytest -q tests`: 10 passed using Temporal's local dev and time-skipping test servers.
- Tested digest rejection and acceptance, worker restart, approval timeout, activity retry, cancellation and dispatch recovery.
- The API still reports its database status rather than Temporal's live workflow state.
- PostgreSQL integration and the full Docker Compose stack remain untested because the local Docker daemon is unavailable.
- This is not the full Week 2 or M1 acceptance gate.
