from dataclasses import replace

import pytest

from security.supply_chain.provenance import MockAttestor, mock_sbom


def test_mock_admission_requires_exact_subject_and_materials():
    attestor = MockAttestor(b"local-test-attestation-key-with-32-bytes")
    value = attestor.attest(
        tenant="team-a", workflow_id="w1", plan_digest="a" * 64,
        source_digest="b" * 64, image_digest="c" * 64, materials=mock_sbom(["fastapi"]),
    )
    context = dict(tenant="team-a", workflow_id="w1", plan_digest="a" * 64,
                   image_digest="c" * 64, materials=mock_sbom(["fastapi"]))
    assert attestor.admit(value, **context)
    assert not attestor.admit(None, **context)
    assert not attestor.admit(value, **{**context, "tenant": "team-b"})
    assert not attestor.admit(value, **{**context, "image_digest": "d" * 64})
    assert not attestor.admit(value, **{**context, "materials": b"changed"})
    assert not attestor.admit(replace(value, source_digest="e" * 64), **context)


def test_invalid_mock_sbom_is_rejected_before_attestation():
    attestor = MockAttestor(b"local-test-attestation-key-with-32-bytes")
    with pytest.raises(ValueError, match="invalid mock SBOM"):
        attestor.attest(
            tenant="team-a", workflow_id="w1", plan_digest="a" * 64,
            source_digest="b" * 64, image_digest="c" * 64,
            materials=b'{"format":"mock-sbom-v1","components":[]}',
        )
