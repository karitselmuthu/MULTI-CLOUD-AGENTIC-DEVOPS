from opentelemetry import trace

from observability.otel.correlation import workflow_span


def test_workflow_operations_share_trace_id_without_request_content():
    workflow_id = "68e4d14d-88f7-40dd-a63d-cf74e0d501ee"
    with workflow_span(workflow_id, "api.read"):
        first = trace.get_current_span().get_span_context().trace_id
    with workflow_span(workflow_id, "worker.plan"):
        second = trace.get_current_span().get_span_context().trace_id
    assert first == second == int(workflow_id.replace("-", ""), 16)
