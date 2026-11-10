"""Local provenance and admission contract; HMAC is a mock for cosign.

Cosign verification: https://docs.sigstore.dev/cosign/verifying/verify/
"""

import hashlib
import hmac
import json
from dataclasses import dataclass


@dataclass(frozen=True)
class MockProvenance:
    tenant: str
    workflow_id: str
    plan_digest: str
    source_digest: str
    image_digest: str
    materials_digest: str
    signature: str


def _payload(value: MockProvenance) -> bytes:
    fields = {key: getattr(value, key) for key in (
        "tenant", "workflow_id", "plan_digest", "source_digest", "image_digest", "materials_digest"
    )}
    return json.dumps(fields, sort_keys=True, separators=(",", ":")).encode()


class MockAttestor:
    def __init__(self, key: bytes):
        if len(key) < 32:
            raise ValueError("mock attestation key must be at least 32 bytes")
        self._key = key

    def attest(self, *, tenant: str, workflow_id: str, plan_digest: str,
               source_digest: str, image_digest: str, materials: bytes) -> MockProvenance:
        value = MockProvenance(tenant, workflow_id, plan_digest, source_digest,
                               image_digest, hashlib.sha256(materials).hexdigest(), "")
        signature = hmac.new(self._key, _payload(value), hashlib.sha256).hexdigest()
        return MockProvenance(**{**value.__dict__, "signature": signature})

    def admit(self, value: MockProvenance, *, tenant: str, workflow_id: str,
              plan_digest: str, image_digest: str, materials: bytes) -> bool:
        if (value.tenant, value.workflow_id, value.plan_digest, value.image_digest) != (
            tenant, workflow_id, plan_digest, image_digest
        ):
            return False
        if value.materials_digest != hashlib.sha256(materials).hexdigest():
            return False
        expected = hmac.new(self._key, _payload(value), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, value.signature)
