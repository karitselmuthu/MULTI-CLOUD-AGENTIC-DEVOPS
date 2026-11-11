"""Server-side Langfuse client configuration; never exposed to the browser.

Source: https://langfuse.com/docs/observability/sdk/overview#quickstart
"""

import os


def configured_langfuse_client():
    public = os.environ.get("LANGFUSE_PUBLIC_KEY")
    secret = os.environ.get("LANGFUSE_SECRET_KEY")
    base_url = os.environ.get("LANGFUSE_BASE_URL")
    if not public or not secret or not base_url:
        raise ValueError("Langfuse public key, secret key and base URL are required")
    loopback = base_url.startswith(("http://127.0.0.1:", "http://localhost:"))
    if not base_url.startswith("https://") and not loopback:
        raise ValueError("Langfuse requires HTTPS outside loopback")
    from langfuse import get_client  # optional observability extra

    return get_client()
