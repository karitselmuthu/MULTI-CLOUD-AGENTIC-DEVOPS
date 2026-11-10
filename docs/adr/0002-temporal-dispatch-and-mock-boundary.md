# ADR 0002: Database backed dispatch into Temporal

Status: accepted for Week 2 mock orchestration.

## Context

Week 1 commits a request to PostgreSQL before a worker can start it. A crash between database commit and Temporal start must not lose the request. A crash after Temporal start but before database acknowledgement must not start a second workflow.

## Decision

Use `received` workflow rows as a durable dispatch queue. The worker polls these rows and starts Temporal with the same workflow ID and `REJECT_DUPLICATE` reuse policy. It then marks the row `queued` and records a dispatch audit event. If the start already happened, it acknowledges the existing workflow. The workflow only calls mock activities and waits for a digest-matching approval signal. Activity timeouts and retry limits are explicit.

## Consequences

The crash window is recoverable for a single dispatcher. Multi-worker dispatch needs row claiming or a dedicated transactional outbox before production. Temporal state is not yet projected to the API. The signal proves only that a caller knows the digest; Week 4 must add approver identity, authorization, policy decisions and change record binding before any real execution.

## Sources

- https://docs.temporal.io/develop/python/workflows/basics
- https://docs.temporal.io/develop/python/workflows/message-passing
- https://docs.temporal.io/develop/python/best-practices/testing-suite
- https://python.temporal.io/temporalio.client.Client.html
- https://docs.temporal.io/encyclopedia/retry-policies
