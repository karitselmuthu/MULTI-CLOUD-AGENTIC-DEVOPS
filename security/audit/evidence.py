"""Deterministic local audit evidence bundle and recovery snapshot."""

import hashlib
import json
from dataclasses import dataclass


@dataclass(frozen=True)
class EvidenceBundle:
    workflow_id: str
    tenant: str
    events: tuple[str, ...]
    digest: str

    @classmethod
    def create(cls, workflow_id: str, tenant: str, events: tuple[str, ...]):
        if not workflow_id or not tenant or not events:
            raise ValueError("evidence context and events are required")
        payload = json.dumps({"workflow_id": workflow_id, "tenant": tenant,
                              "events": events}, sort_keys=True, separators=(",", ":"))
        return cls(workflow_id, tenant, events, hashlib.sha256(payload.encode()).hexdigest())

    def verify(self) -> bool:
        return self == self.create(self.workflow_id, self.tenant, self.events)
