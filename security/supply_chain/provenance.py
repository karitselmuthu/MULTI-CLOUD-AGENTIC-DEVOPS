"""Local provenance and admission contract; HMAC is a mock for cosign.

Cosign verification: https://docs.sigstore.dev/cosign/verifying/verify/
"""

import hashlib
import hmac
import json
from dataclasses import dataclass


def mock_sbom(components: list[str]) -> bytes:
    """Return a deliberately narrow local SBOM fixture, not CycloneDX or SPDX."""
    if not components or any(not isinstance(item, str) or not item for item in components):
        raise ValueError("mock SBOM components required")
    return json.dumps({"format": "mock-sbom-v1", "components": sorted(set(components))},
                      sort_keys=True, separators=(",", ":")).encode()


def valid_mock_sbom(materials: bytes) -> bool:
    try:
        value = json.loads(materials)
    except (TypeError, ValueError, UnicodeError):
        return False
    return (
        isinstance(value, dict)
        and set(value) == {"format", "components"}
        and value["format"] == "mock-sbom-v1"
        and isinstance(value["components"], list)
        and bool(value["components"])
        and all(isinstance(item, str) and bool(item) for item in value["components"])
    )


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
        if not valid_mock_sbom(materials):
            raise ValueError("invalid mock SBOM")
        value = MockProvenance(tenant, workflow_id, plan_digest, source_digest,
                               image_digest, hashlib.sha256(materials).hexdigest(), "")
        signature = hmac.new(self._key, _payload(value), hashlib.sha256).hexdigest()
        return MockProvenance(**{**value.__dict__, "signature": signature})

    def admit(self, value: MockProvenance | None, *, tenant: str, workflow_id: str,
              plan_digest: str, image_digest: str, materials: bytes) -> bool:
        if value is None:
            return False
        if not valid_mock_sbom(materials):
            return False
        if (value.tenant, value.workflow_id, value.plan_digest, value.image_digest) != (
            tenant, workflow_id, plan_digest, image_digest
        ):
            return False
        if value.materials_digest != hashlib.sha256(materials).hexdigest():
            return False
        expected = hmac.new(self._key, _payload(value), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, value.signature)
