"""Concurrent local executor load; this is not a cloud throughput benchmark."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from integrations.tacos.mock import MockTacos, TacosRun, Workspace
from security.identity.broker import MockWorkloadBroker
from security.identity.tokens import ApprovalClaims, TokenVerifier


def test_concurrent_mock_applies_do_not_exceed_tenant_budget():
    verifier = TokenVerifier(b"local-test-signing-key-with-32-plus-bytes")
    broker = MockWorkloadBroker(verifier)
    tacos = MockTacos(verifier)
    workspace = Workspace("team-a", "aws", "sandbox", 5)
    expiry = datetime.now(timezone.utc) + timedelta(minutes=5)

    def apply_one(index: int) -> str:
        workflow_id = f"load-{index}"
        digest = f"{index:064x}"
        tacos.plan(TacosRun(workspace, workflow_id, digest,
                            "engineer@example.com", None, 1, "planned"))
        approval = verifier.sign(ApprovalClaims(
            workflow_id=workflow_id, plan_digest=digest,
            environment="sandbox", requester="engineer@example.com",
            approver="reviewer@example.com", expires_at=expiry,
        ))
        workload = broker.issue(tenant="team-a", workflow_id=workflow_id, plan_digest=digest)
        try:
            return tacos.apply(workflow_id, approval, workload).status
        except PermissionError as exc:
            assert "budget" in str(exc)
            return "blocked"

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(apply_one, range(20)))

    assert results.count("applied") == 5
    assert results.count("blocked") == 15
    assert tacos.spent(workspace) == 5
