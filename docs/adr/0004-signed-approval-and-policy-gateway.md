# ADR 0004: Verify approval and tool policy at execution

Status: accepted for the local mock path.

## Context

A plan digest sent as a Temporal signal can be copied by any caller with access to the workflow. The plan must be bound to the requester, environment and change record, and an agent must not bypass tool permissions.

## Decision

Use HMAC-SHA256 signed, short-lived claims for local agent identity and approval. Verify the approval once when the workflow receives it and again in the mock execution activity. The execution activity issues a short-lived devops agent token and calls a local gateway. The gateway verifies token scope and asks OPA to evaluate a deny-by-default Rego policy. The only executable tool returns a simulated result.

## Consequences

Incorrect or expired approvals leave the workflow waiting until the original 24-hour deadline. Missing OPA or signing configuration blocks execution. The shared key and test-issued claims are placeholders for enterprise workload identity and an authenticated approval service. The gateway currently exposes a Python API, not an MCP network transport.

## Sources

- https://docs.python.org/3/library/hmac.html
- https://www.openpolicyagent.org/docs/policy-language
- https://www.openpolicyagent.org/docs/cli
- https://docs.temporal.io/develop/python/workflows/message-passing
