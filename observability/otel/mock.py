"""In-memory trace and incident correlation, shaped for future OTel export.

GenAI attribute names: https://opentelemetry.io/docs/specs/semconv/registry/attributes/gen-ai/
"""

from dataclasses import dataclass
from uuid import uuid4


@dataclass(frozen=True)
class TraceEvent:
    trace_id: str
    tenant: str
    workflow_id: str
    phase: str
    status: str
    attributes: dict[str, str]


@dataclass(frozen=True)
class Incident:
    tenant: str
    workflow_id: str
    trace_id: str
    failed_phases: tuple[str, ...]


class MockTelemetry:
    def __init__(self):
        self._events: list[TraceEvent] = []
        self._trace_ids: dict[tuple[str, str], str] = {}

    def record(self, *, tenant: str, workflow_id: str, phase: str,
               status: str, trace_id: str | None = None) -> TraceEvent:
        if status not in {"ok", "failed"}:
            raise ValueError("unsupported status")
        attributes = {"workflow.id": workflow_id, "tenant.id": tenant}
        if phase == "planning":
            attributes["gen_ai.operation.name"] = "invoke_agent"
        key = (tenant, workflow_id)
        existing_trace_id = self._trace_ids.get(key)
        if existing_trace_id is not None and trace_id is not None and trace_id != existing_trace_id:
            raise ValueError("trace id changed within workflow")
        actual_trace_id = existing_trace_id or trace_id or uuid4().hex
        self._trace_ids[key] = actual_trace_id
        event = TraceEvent(actual_trace_id, tenant, workflow_id, phase, status, attributes)
        self._events.append(event)
        return event

    def incident(self, tenant: str, workflow_id: str) -> Incident | None:
        events = [event for event in self._events
                  if event.tenant == tenant and event.workflow_id == workflow_id]
        failed = tuple(event.phase for event in events if event.status == "failed")
        if not failed:
            return None
        return Incident(tenant, workflow_id, events[0].trace_id, failed)

    def failure_count(self, tenant: str) -> int:
        return sum(event.status == "failed" for event in self._events if event.tenant == tenant)
