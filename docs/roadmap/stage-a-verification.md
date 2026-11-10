# Stage A local acceptance evidence

Date: 2026-11-10 (Asia/Kolkata)

- Python 3.12, FastAPI 0.162.2, Temporal Python SDK 1.35.0, LangGraph 1.2.20, PostgreSQL 16.14 and OPA 1.22.2.
- `OPA_BIN=/tmp/opa_darwin_arm64 TEST_DATABASE_URL=... .venv/bin/python -m pytest -q tests`: 19 passed against isolated PostgreSQL, Temporal local test servers and OPA.
- `opa test security/opa -v`: 5 passed.
- API flow tested: submit request, dispatch, observe plan, reject forged approval, accept matching signed approval, observe simulated completion and audit events.
- Worker restart, activity retry, cancellation, idempotent dispatch and approval timeout tested.
- AWS and Azure plans are evaluated against golden requests; unsupported modules and changed model targets fail.
- Local PostgreSQL persisted an accepted request across a new API instance.

## External acceptance still open

AWS/Azure sandbox provisioning, enterprise identity, ITSM, TACOS, Kubernetes and supply-chain controls need their later workstreams and test systems. Stage A runs only mock execution. GitHub Actions validation is configured but must be observed after push.
