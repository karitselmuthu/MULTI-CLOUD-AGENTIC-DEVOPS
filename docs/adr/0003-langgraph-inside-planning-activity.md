# ADR 0003: Run planning graph inside a Temporal activity

Status: accepted for Week 3 mock planning.

## Context

Temporal requires workflow code to be replay deterministic. A future model call will be nondeterministic and belongs outside the workflow function. The plan also needs a structured contract and a stable digest before approval.

## Decision

Run a short LangGraph state graph inside `prepare_mock_plan`, a Temporal activity. Use separate nodes for validation, mock tool lookup, gateway proposal and finalization. Validate the gateway output with Pydantic and reject any change to the requested target. Derive the plan digest from canonical JSON. Keep the gateway and tool as protocols with offline mocks.

## Consequences

Temporal retries the entire planning activity if it fails. The mock gateway is deterministic, so the same request yields the same plan digest. Future real model use needs model routing, quotas, data handling, evaluation thresholds and persistent graph checkpoints when reasoning loops become long lived.

## Sources

- https://docs.langchain.com/oss/python/langgraph/graph-api
- https://docs.temporal.io/develop/python/workflows/basics
- https://pydantic.dev/docs/validation/latest/concepts/fields/
