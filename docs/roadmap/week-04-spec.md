# Week 4: local security foundation

Status: implemented for the mock-only Stage A path.

## Scope

- Issue and verify short-lived, run-scoped agent tokens and signed approval claims.
- Bind approvals to workflow ID, exact plan digest, environment, requester and change record.
- Deny an approver who is also the requester.
- Route mock tool calls through a gateway that verifies tokens and asks OPA for every decision.
- Deny unknown tools, wrong roles, mismatched workflows, unapproved execution and production mock execution.
- Require signed approvals at the API and again in the Temporal execution activity.

## Trust boundaries

The HTTP request and model proposal are untrusted. The signing key is trusted local configuration and must not be checked in. Temporal signals are untrusted until the approval activity verifies the signature and context. OPA is mandatory for mock execution; an unavailable policy engine denies the call.

## Limitations

This is a local prototype. There is no enterprise identity provider, authenticated approver enrollment, network MCP protocol server, secret broker, rate limiting, audit immutability or real mutation adapter. Signing tokens with a local shared key is suitable only for isolated mock development. The API intake and read endpoints are not externally authenticated. Do not expose this service to an untrusted network.
