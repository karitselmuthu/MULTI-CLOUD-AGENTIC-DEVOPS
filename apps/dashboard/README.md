# Local delivery dashboard

The React dashboard connects to the FastAPI control plane through Vite's local proxy. It shows a request form, current plan digest and source references, approval state, audit activity, and the simulated deployment report. The resource section displays a labeled simulation; it is not a cloud inventory.

Start PostgreSQL, the API, Temporal and the worker as described in the repository README. In the API terminal, configure a local requester and a fresh token:

```sh
export LOCAL_DASHBOARD_REQUESTER=engineer@example.com
export LOCAL_DASHBOARD_TOKEN="$(openssl rand -hex 24)"
uv run --locked --extra test uvicorn apps.api.main:app --reload
```

In another terminal:

```sh
cd apps/dashboard
npm ci
npm run dev
```

Open `http://127.0.0.1:5173` and enter the token. The requester's email in the form must equal `LOCAL_DASHBOARD_REQUESTER`. The token is kept in React state for this browser tab. The dashboard API is disabled when either environment variable is absent. This shared local token is a development control, not enterprise identity or tenant authorization. A real portal must use authenticated users and tenant-scoped permissions before it is exposed outside an isolated workstation.

The approval input accepts an externally issued signed approval token. The dashboard does not mint approvals. See [ADR 0004](../../docs/adr/0004-signed-approval-and-policy-gateway.md).
