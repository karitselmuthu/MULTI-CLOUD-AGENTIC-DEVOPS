# Local delivery dashboard

The React dashboard connects to the FastAPI control plane through Vite's local proxy. It shows a request form, current plan digest and source references, approval state, audit activity, and the simulated deployment report. The resource section displays a labeled simulation; it is not a cloud inventory.

The request form requires a cost center in the browser, checks field values before submission, and accepts up to 2,000 characters of plain-text details. It keeps an unfinished draft in session storage and reuses its idempotency key while retrying an uncertain submission. The API accepts older requests without the new fields for compatibility. See the [FE-01–FE-13 acceptance matrix](../../docs/roadmap/frontend-acceptance.md) for verified local behavior and remaining connected-system gates.

Start PostgreSQL and Temporal as described in the repository README. From the repository root, create a private shared environment file once:

```sh
uv run --locked python -m apps.cli.local_env
```

The file is ignored by Git and created with owner-only permissions. Keep it private. In **each** API, worker, and approval terminal, run `set -a; source .env; set +a` from the repository root. Restart any existing API or worker process after loading it. Start the API and worker in separate terminals:

```sh
uv run --locked uvicorn apps.api.main:app --reload
```

```sh
uv run --locked python -m orchestration.temporal.workers.mock_worker
```

Start the frontend in another terminal:

```sh
cd apps/dashboard
npm ci
npm run dev
```

Open `http://127.0.0.1:5173` and enter the `LOCAL_DASHBOARD_TOKEN` value from `.env`. The requester's email in the form must equal `LOCAL_DASHBOARD_REQUESTER`. The token is kept in React state for this browser tab. The dashboard API is disabled when either environment variable is absent. This shared local token is a development control, not enterprise identity or tenant authorization. A real portal must use authenticated users and tenant-scoped permissions before it is exposed outside an isolated workstation.

Submit an AWS request with region `us-east-1` or an Azure request with region `eastus`; both use approved module `sandbox-api`. When a plan reaches **Awaiting approval**, review its digest, then select **Show local mock token** in the plan panel. The token appears in the approval field; select **Submit approval** to continue. No approver email is needed for this local simulation.

If you prefer the terminal, run this in a separate terminal with the same `.env` loaded:

```sh
uv run --locked python -m apps.cli.local_approval --workflow-id <workflow-uuid>
```

Copy the printed signed token into the dashboard's approval field. The simulated approver is `local-mock-reviewer`, distinct from the requester. The token expires after 10 minutes and is bound to the workflow, exact plan digest, environment, requester, and change record. The button and CLI are isolated local mock issuers, not authenticated approval flows. Do not enable them in shared or production deployments. Install the OPA CLI (`brew install opa` on macOS) before approval execution; a missing OPA binary denies the mock tool call. See [ADR 0004](../../docs/adr/0004-signed-approval-and-policy-gateway.md).

If the button or CLI reports **403**, restart the API after sourcing `.env`, then sign into the dashboard again with the token from that same file. A token from an earlier API start will not work. Run `set -a; source .env; set +a` in the worker terminal and restart it too, so both processes use the same signing key.
