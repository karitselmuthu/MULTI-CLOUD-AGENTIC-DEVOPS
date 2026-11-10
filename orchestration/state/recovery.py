"""File-backed local recovery exercise for non-secret workflow metadata."""

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class RecoverySnapshot:
    tenant: str
    workflow_id: str
    plan_digest: str
    deployment_revision: str
    status: str


class MockRecoveryStore:
    def __init__(self, path: Path):
        self.path = path

    def backup(self, snapshot: RecoverySnapshot) -> str:
        payload = json.dumps(asdict(snapshot), sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(payload.encode()).hexdigest()
        encoded = json.dumps({"snapshot": asdict(snapshot), "digest": digest}, sort_keys=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(encoded)
        temporary.replace(self.path)
        return digest

    def restore(self, *, tenant: str) -> RecoverySnapshot:
        document = json.loads(self.path.read_text())
        payload = json.dumps(document["snapshot"], sort_keys=True, separators=(",", ":"))
        expected = hashlib.sha256(payload.encode()).hexdigest()
        if expected != document["digest"]:
            raise ValueError("recovery snapshot checksum mismatch")
        snapshot = RecoverySnapshot(**document["snapshot"])
        if snapshot.tenant != tenant:
            raise PermissionError("recovery snapshot belongs to another tenant")
        return snapshot
