# ADR 0007: Backstage views require an authenticated backend

Status: Accepted for the integration scaffold.

## Context

The workstation dashboard uses a shared local token. Backstage users need per-user and tenant-scoped status without exposing that token or another service secret to the browser.

## Decision

`apps/developer-portal/` exports a Backstage frontend page using discovery and authenticated fetch APIs. It calls a `multicloud-delivery` backend contract. The host backend must authenticate the user, map tenant/requester scope, and use scoped service credentials to call the control plane. This repository does not register a host backend or claim a live Backstage deployment. The existing `apps/backstage-plugin/` catalog and template examples remain available.

## Consequences

The plugin package typechecks independently, but end-to-end portal acceptance waits for a Backstage host and backend. A generic proxy with an injected shared authorization header was rejected because any authorized Backstage user could reuse that header's authority against the upstream service.

Sources: [Backstage frontend plugins](https://backstage.io/docs/frontend-system/architecture/plugins/), [authenticated fetch](https://backstage.io/docs/next/plugins/call-existing-api/), [proxy threat model](https://backstage.io/docs/next/overview/threat-model/#proxy).
