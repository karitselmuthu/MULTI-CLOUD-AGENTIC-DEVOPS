from datetime import datetime, timedelta, timezone

import pytest

from integrations.jira.mock import MockChangeService
from security.identity.broker import MockWorkloadBroker
from security.identity.tokens import ApprovalClaims, TokenVerifier, WorkloadClaims


KEY = b"local-test-signing-key-with-32-plus-bytes"


def test_short_lived_workload_token_and_scope():
    verifier = TokenVerifier(KEY)
    broker = MockWorkloadBroker(verifier)
    token = broker.issue(tenant="team-a", workflow_id="w1", plan_digest="a" * 64)
    claims = verifier.verify(token, WorkloadClaims)
    assert claims.tenant == "team-a"
    assert claims.role == "tacos-executor"
    verifier.revoke(token)
    with pytest.raises(PermissionError):
        verifier.verify(token, WorkloadClaims)
    with pytest.raises(ValueError, match="five minutes"):
        broker.issue(tenant="team-a", workflow_id="w1", plan_digest="a" * 64,
                     lifetime=timedelta(hours=1))


def test_change_record_binds_plan_approval_and_cab_evidence():
    verifier = TokenVerifier(KEY)
    service = MockChangeService(verifier)
    record = service.create(tenant="team-a", workflow_id="w1", plan_digest="a" * 64,
                            requester="engineer@example.com", environment="sandbox")
    assert service.create(tenant="team-a", workflow_id="w1", plan_digest="a" * 64,
                          requester="engineer@example.com", environment="sandbox") == record
    token = verifier.sign(ApprovalClaims(
        workflow_id="w1", plan_digest="a" * 64, environment="sandbox",
        requester="engineer@example.com", change_record=record.change_id,
        approver="reviewer@example.com",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    ))
    with pytest.raises(ValueError, match="CAB evidence"):
        service.approve(record.change_id, token, b"")
    approved = service.approve(record.change_id, token, b"CAB reviewed plan abc")
    assert approved.status == "approved"
    assert len(approved.cab_evidence_digest) == 64
    with pytest.raises(ValueError, match="changed"):
        service.approve(record.change_id, token, b"different evidence")


def test_change_record_rejects_wrong_plan():
    verifier = TokenVerifier(KEY)
    service = MockChangeService(verifier)
    record = service.create(tenant="team-a", workflow_id="w1", plan_digest="a" * 64,
                            requester="engineer@example.com", environment="sandbox")
    bad = verifier.sign(ApprovalClaims(
        workflow_id="w1", plan_digest="b" * 64, environment="sandbox",
        requester="engineer@example.com", change_record=record.change_id,
        approver="reviewer@example.com",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    ))
    with pytest.raises(PermissionError, match="does not match"):
        service.approve(record.change_id, bad, b"CAB reviewed")
