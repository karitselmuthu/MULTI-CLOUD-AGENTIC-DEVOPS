from datetime import datetime, timedelta, timezone

import pytest

from integrations.tacos.mock import MockTacos, TacosRun, Workspace
from security.identity.tokens import ApprovalClaims, TokenVerifier, WorkloadClaims


def tokens(tenant="team-a", plan_digest="a" * 64):
    verifier = TokenVerifier(b"local-test-signing-key-with-32-plus-bytes")
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
    approval = verifier.sign(ApprovalClaims(
        workflow_id="w1", plan_digest=plan_digest,
        environment="sandbox", requester="engineer@example.com",
        approver="reviewer@example.com", expires_at=expires_at,
    ))
    workload = verifier.sign(WorkloadClaims(
        tenant=tenant, role="tacos-executor", workflow_id="w1",
        plan_digest=plan_digest, expires_at=expires_at,
    ))
    return verifier, approval, workload


def run(workspace, cost=3):
    return TacosRun(workspace, "w1", "a" * 64, "engineer@example.com", None, cost, "planned")


def test_mock_run_requires_exact_approval_and_tenant_scope():
    verifier, approval, workload = tokens()
    tacos = MockTacos(verifier)
    workspace = Workspace("team-a", "aws", "sandbox", 10)
    tacos.plan(run(workspace))
    assert tacos.apply("w1", approval, workload).status == "applied"
    assert tacos.apply("w1", approval, workload).status == "applied"


def test_cross_tenant_and_wrong_digest_denied():
    verifier, approval, wrong_tenant = tokens(tenant="team-b")
    tacos = MockTacos(verifier)
    workspace = Workspace("team-a", "azure", "sandbox", 10)
    tacos.plan(run(workspace))
    with pytest.raises(PermissionError, match="workload scope"):
        tacos.apply("w1", approval, wrong_tenant)
    _, wrong_approval, _ = tokens(plan_digest="b" * 64)
    with pytest.raises(PermissionError, match="approval does not match"):
        tacos.apply("w1", wrong_approval, tokens()[2])


def test_budget_and_drift_block_apply():
    verifier, approval, workload = tokens()
    workspace = Workspace("team-a", "aws", "sandbox", 2)
    tacos = MockTacos(verifier)
    tacos.plan(run(workspace, cost=3))
    with pytest.raises(PermissionError, match="budget"):
        tacos.apply("w1", approval, workload)
    workspace = Workspace("team-a", "aws", "sandbox", 10)
    tacos = MockTacos(verifier)
    tacos.plan(run(workspace))
    tacos.record_drift(workspace)
    assert tacos.has_drift(workspace)
    with pytest.raises(PermissionError, match="drift"):
        tacos.apply("w1", approval, workload)


def test_plan_idempotency_rejects_changed_request():
    tacos = MockTacos(tokens()[0])
    workspace = Workspace("team-a", "aws", "sandbox", 10)
    tacos.plan(run(workspace))
    with pytest.raises(ValueError, match="reused"):
        tacos.plan(run(workspace, cost=4))
