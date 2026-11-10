from dataclasses import replace

from security.supply_chain.provenance import MockAttestor


def test_mock_admission_requires_exact_subject_and_materials():
    attestor = MockAttestor(b"local-test-attestation-key-with-32-bytes")
    value = attestor.attest(
        tenant="team-a", workflow_id="w1", plan_digest="a" * 64,
        source_digest="b" * 64, image_digest="c" * 64, materials=b"mock-package-list",
    )
    context = dict(tenant="team-a", workflow_id="w1", plan_digest="a" * 64,
                   image_digest="c" * 64, materials=b"mock-package-list")
    assert attestor.admit(value, **context)
    assert not attestor.admit(value, **{**context, "tenant": "team-b"})
    assert not attestor.admit(value, **{**context, "image_digest": "d" * 64})
    assert not attestor.admit(value, **{**context, "materials": b"changed"})
    assert not attestor.admit(replace(value, source_digest="e" * 64), **context)
