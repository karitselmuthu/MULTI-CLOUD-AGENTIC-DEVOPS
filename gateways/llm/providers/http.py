"""Authenticated HTTPS adapter for an internal structured model service.

Source: https://www.python-httpx.org/quickstart/#sending-json-encoded-data
"""

import httpx

from apps.api.contracts import RequestCreate
from knowledge.retrieval.qdrant import KnowledgeHit


class HTTPModelProvider:
    def __init__(self, endpoint: str, token: str, client: httpx.Client | None = None):
        loopback = endpoint.startswith(("http://127.0.0.1:", "http://localhost:"))
        if (not endpoint.startswith("https://") and not loopback) or not token:
            raise ValueError("model endpoint requires HTTPS outside loopback and a token")
        self.endpoint = endpoint
        self.token = token
        self.client = client or httpx.Client(timeout=3.0, follow_redirects=False)

    def propose(self, request: RequestCreate, *, context: tuple[KnowledgeHit, ...] = ()) -> dict:
        response = self.client.post(
            self.endpoint,
            headers={"Authorization": f"Bearer {self.token}"},
            json={"request": request.model_dump(mode="json"),
                  "context": [{"source": hit.source, "revision": hit.revision,
                               "excerpt": hit.excerpt} for hit in context]},
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict) or not isinstance(payload.get("proposal"), dict):
            raise ValueError("model service returned no structured proposal")
        return payload["proposal"]
