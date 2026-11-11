# OpenTelemetry GenAI tracing

`TracedModelGateway` creates a model operation span with `gen_ai.operation.name` and no prompt or retrieved document payload. `workflow_span` gives API detail and worker planning operations a stable workflow-derived trace ID for local correlation. The repository does not yet configure an OTLP exporter or standard Temporal trace-context propagation; the derived ID is a local bridge and is not a substitute for a connected distributed trace pipeline.

Sources: [OpenTelemetry Python instrumentation](https://opentelemetry.io/docs/languages/python/instrumentation/) and [GenAI semantic attributes](https://opentelemetry.io/docs/specs/semconv/registry/attributes/gen-ai/).
