"""Stable trace context for workflow-bound API and worker operations.

Source: https://opentelemetry.io/docs/languages/python/instrumentation/
"""

import hashlib
from contextlib import contextmanager
from uuid import UUID

from opentelemetry import trace


@contextmanager
def workflow_span(workflow_id: str, operation: str):
    trace_id = UUID(workflow_id).int
    parent_id = int.from_bytes(hashlib.sha256(workflow_id.encode()).digest()[:8], "big") or 1
    parent = trace.NonRecordingSpan(trace.SpanContext(
        trace_id=trace_id, span_id=parent_id, is_remote=True,
        trace_flags=trace.TraceFlags(trace.TraceFlags.SAMPLED),
        trace_state=trace.TraceState(),
    ))
    with trace.use_span(parent, end_on_exit=False):
        with trace.get_tracer("enterprise-devops.workflow").start_as_current_span(operation) as span:
            span.set_attribute("workflow.id", workflow_id)
            yield span
