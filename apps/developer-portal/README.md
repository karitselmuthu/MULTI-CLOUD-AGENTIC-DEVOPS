# Backstage developer portal package

This package exports a Backstage frontend plugin with a request list and detail view at `/multicloud-delivery`. It uses Backstage's discovery and authenticated fetch APIs to call a backend plugin named `multicloud-delivery`. The browser receives no control-plane service token.

The repository does not contain a running Backstage host or the required backend plugin. Register this package in a host app only after the backend route authenticates the Backstage user, maps that user to a tenant/requester, and calls the control plane with scoped service credentials. The backend must provide `GET /workflows` and `GET /workflows/{id}` with the shapes used by `RequestPage.tsx`; it must enforce tenant scope server-side. The current `LOCAL_DASHBOARD_TOKEN` is a workstation-only credential and must not be copied into Backstage proxy configuration. The older `apps/backstage-plugin/` catalog and template examples remain intact.

Run `npm ci && npm run build` to typecheck and emit the isolated plugin package under `dist/`. React, React Router and the Backstage frontend API are peer dependencies supplied by a compatible host app. A host-app integration and browser acceptance test remain open.

The current Backstage frontend package requires React Router 6. The lockfile uses the latest patched 6.30.6 line that resolves the reported high-severity route advisories, but npm audit still reports moderate advisories in Router 6. This package is not deployed; a host-app dependency update and vulnerability review remain a release gate.

Sources: [Backstage frontend plugins](https://backstage.io/docs/frontend-system/architecture/plugins/), [calling a backend API](https://backstage.io/docs/next/plugins/call-existing-api/), and [proxy threat model](https://backstage.io/docs/next/overview/threat-model/#proxy).
