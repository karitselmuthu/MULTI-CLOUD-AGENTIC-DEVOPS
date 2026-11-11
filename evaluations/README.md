# Local agent evaluation gate

`golden_requests/` and `expected_plans/` contain deterministic AWS and Azure planner cases. `tests/unit/test_planning.py` verifies plan fields and stable digests. `tests/security/test_prompt_injection.py` rejects a model proposal that changes target cloud or environment and one that attempts to inject a tool call into the structured plan. `tests/security/test_gateway.py` checks tool authorization. These are mock regression cases, not a measured production model evaluation or a comprehensive prompt-injection benchmark.

Run with `uv run --locked --extra test python -m pytest -q tests/unit/test_planning.py tests/security/test_prompt_injection.py tests/security/test_gateway.py` and `opa test security/opa -v`.

`retrieval_quality.py` measures recall, precision and reciprocal rank for approved reference searches. `tests/unit/test_retrieval_evaluation.py` is a deterministic local gate. The deployment, security and workflow reliability checks live in separate `evaluations/` modules and are tested independently. A connected embedding model and representative enterprise corpus are still needed before setting production RAG thresholds.
