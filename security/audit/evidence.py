"""Deterministic local audit evidence bundle and recovery snapshot."""

import hashlib
import json
from dataclasses import dataclass


@dataclass(frozen=True)
class EvidenceBundle:
    workflow_id: str
    tenant: str
    events: tuple[str, ...]
    event_hashes: tuple[str, ...]
    digest: str

    @classmethod
    def create(cls, workflow_id: str, tenant: str, events: tuple[str, ...]):
        if not workflow_id or not tenant or not events:
            raise ValueError("evidence context and events are required")
        seed = json.dumps({"workflow_id": workflow_id, "tenant": tenant},
                          sort_keys=True, separators=(",", ":"))
        previous = hashlib.sha256(seed.encode()).hexdigest()
        hashes: list[str] = []
        for event in events:
            if not event:
                raise ValueError("audit events cannot be empty")
            previous = hashlib.sha256(f"{previous}:{event}".encode()).hexdigest()
            hashes.append(previous)
        return cls(workflow_id, tenant, events, tuple(hashes), previous)

    def verify(self) -> bool:
        return self == self.create(self.workflow_id, self.tenant, self.events)
