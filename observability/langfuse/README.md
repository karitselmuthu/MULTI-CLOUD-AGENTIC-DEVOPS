# Langfuse trace configuration

Install the optional `observability` Python extra and configure `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` and `LANGFUSE_BASE_URL` in the worker environment. The factory fails closed if any value is missing or if a non-loopback base URL is cleartext. The SDK is server-side only; never pass the secret key to the React dashboard or Backstage. The current wrapper records operation and target metadata, not request bodies, retrieved excerpts or approval tokens.

Source: [Langfuse Python SDK quickstart](https://langfuse.com/docs/observability/sdk/overview#quickstart).
