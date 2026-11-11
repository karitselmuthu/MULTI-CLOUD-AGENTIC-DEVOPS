# Frontend acceptance against FE-01–FE-13

This matrix records local evidence for the screenshot acceptance scenarios. The React dashboard is a local mock UI. The Backstage package has no running host, backend plugin, SSO provider or catalog connection. A local pass does not certify an enterprise deployment.

| ID | Current result | Evidence and remaining gate |
| --- | --- | --- |
| FE-01 | Open | No Entra ID or IAM Identity Center session, role claims or hosted SSO flow. The local token is a single-requester development control. |
| FE-02 | Local pass | Empty form submission stays on the form and shows eight field errors, including cloud, environment, region and cost center. Chrome interaction and `npm test` cover this. API keeps cost center optional for older clients. |
| FE-03 | Local pass | The form rejects HTML and descriptions over 2,000 characters; API validation rejects both. Chrome confirmed a script string did not execute. No rich-text input is supported. |
| FE-04 | Local pass | A valid local submission returns HTTP 202 and an ID, and the dashboard shows **Pending plan**. The API's durable initial state remains `received`; the UI groups `received` and `queued` as pending planning. |
| FE-05 | Partial | A simulated status update appeared without browser refresh during local polling. The dashboard checks every two seconds after each completed request. A measured five-second SLA and 500-user behavior remain open. |
| FE-06 | Open | Mock plan digest and approved references render. Terraform diff, cost estimate, risk score and role-scoped approve/reject controls are not supplied by the backend. The UI labels their absence. |
| FE-07 | Local security pass, response differs | API tests show a requester cannot read another request. The API deliberately returns 404 for both missing and inaccessible IDs, hiding whether the ID exists. The screenshot expects 403; no tenant/role identity integration exists yet. |
| FE-08 | Open | Backstage catalog descriptor exists, but no host, registration or catalog sync runs. |
| FE-09 | Open | The Backstage template uses `debug:log`; it does not call the control plane. An authenticated backend action is required. |
| FE-10 | Local pass | With the API stopped, Chrome showed a retry message, retained the form and re-enabled submit. The draft survived reload. The same idempotency key is retained until POST succeeds. |
| FE-11 | Partial | Chrome's accessibility tree shows names for all visible inputs, selects and buttons. Field alerts, semantic form submission, live status and visible keyboard focus are present. A human screen-reader, keyboard-order and contrast audit is still required for WCAG 2.1 AA. |
| FE-12 | Open | No 500-user dashboard run or p95 page-load measurement has been executed. Polling performance is not certified. |
| FE-13 | Local pass for token rotation | Rotating the local token sent Chrome back to the token screen and retained the draft; reconnecting with a new token restored it. SSO silent refresh is not implemented. |

## Verification run

- `apps/dashboard`: three request-validation tests and production build passed.
- Control-plane API: eight selected unit tests passed, including description bounds and requester isolation.
- Isolated Chrome + temporary SQLite API: verified FE-02, FE-03, FE-04, a simulated FE-05 status change, FE-10 outage/draft recovery, and FE-13 local token rotation.
- The CI Stage A dashboard job now runs `npm test` before `npm run build`.

The browser checks used an isolated local Chrome profile and test-only token. They did not exercise cloud provisioning, real approvals or a Backstage host.
