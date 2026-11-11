# ADR 0006: Model selection stays in the gateway

Status: Accepted for the local prototype.

## Context

Agents should not import provider SDKs or choose endpoints. Model requests also need reasoning, latency, estimated cost, residency and tenant budget controls.

## Decision

Keep provider adapters under `gateways/llm/providers/`, route policy under `routing/`, and a tenant quota ledger under `quotas/`. The router first filters providers against every requirement, then tries eligible providers by estimated cost and latency. It falls back only on transport failures and releases a failed local quota reservation. Invalid structured output and policy denial stop the call. The quota ledger is process-local and is not an enterprise billing control.

## Consequences

Profile claims about residency, latency and price are operator metadata until measured and attested. A connected deployment needs a distributed quota store, idempotent accounting, provider authentication and measured regression gates. Provider responses are still validated by the planner before a plan is accepted.

Source: [HTTPX transport errors](https://www.python-httpx.org/advanced/transports/).
