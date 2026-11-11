"""Model tracing without recording request text or retrieved documents.

Sources: https://opentelemetry.io/docs/languages/python/instrumentation/
         https://langfuse.com/docs/observability/sdk/instrumentation
"""

from typing import Protocol

from opentelemetry import trace

from apps.api.contracts import RequestCreate
from gateways.llm.model import ModelGateway
from agents.knowledge.retrieval import KnowledgeHit
from observability.langfuse import configured_langfuse_client


class ObservationClient(Protocol):
    def start_as_current_observation(self, **kwargs): ...


class TracedModelGateway:
    def __init__(self, delegate: ModelGateway, langfuse: ObservationClient | None = None):
        self.delegate = delegate
        self.langfuse = langfuse

    def propose(self, request: RequestCreate, *, context: tuple[KnowledgeHit, ...] = ()) -> dict:
        tracer = trace.get_tracer("enterprise-devops.model-gateway")
        with tracer.start_as_current_span("model.propose") as span:
            span.set_attribute("gen_ai.operation.name", "chat")
            span.set_attribute("cloud.target", request.cloud.value)
            if self.langfuse is None:
                return self.delegate.propose(request, context=context)
            with self.langfuse.start_as_current_observation(
                as_type="generation", name="plan-proposal",
                metadata={"cloud": request.cloud.value, "environment": request.environment.value},
            ) as generation:
                result = self.delegate.propose(request, context=context)
                generation.update(metadata={"status": "structured-output-received"})
                return result
