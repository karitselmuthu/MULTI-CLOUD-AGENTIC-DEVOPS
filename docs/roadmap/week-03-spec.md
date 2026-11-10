# Week 3: mock planning agent

Status: deterministic planning slice.

## Scope

- Validate intake again inside the planning activity.
- Use a LangGraph state graph for request validation, mock module lookup, model proposal and plan finalization.
- Require a structured `PlanProposal`; reject model output that changes the requested cloud, environment or application.
- Use a model gateway protocol with a deterministic, offline mock implementation.
- Evaluate AWS and Azure golden requests and expected plan fields in tests.

## Boundaries

The mock module catalog only recognizes `sandbox-api`. No real LLM, cloud tool, MCP call or repository write is available. The graph runs inside a Temporal activity; Temporal remains responsible for durable retries and approval waiting. LangGraph checkpointing is deferred until the planning graph contains recoverable multi-step reasoning.

## Exit checks

- Golden AWS/Azure plans have stable digests and expected fields.
- Unsupported modules and model proposals that change the target fail closed.
- Temporal workflow integration continues to pass.
