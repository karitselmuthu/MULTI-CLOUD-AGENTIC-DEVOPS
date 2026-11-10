"""Cross-cloud local acceptance of the contracts; no external systems are contacted."""

import json
from datetime import datetime, timedelta, timezone

import pytest

from agents.planning.graph import build_graph
from gateways.llm.model import MockModelGateway
from integrations.jira.mock import MockChangeService
from integrations.tacos.mock import MockTacos, TacosRun, Workspace
from orchestration.state.contracts import ApprovalCheck, WorkflowInput
from orchestration.temporal.activities.delivery import simulate_delivery
from security.identity.broker import MockWorkloadBroker
from security.identity.tokens import ApprovalClaims, TokenVerifier
from security.supply_chain.provenance import MockAttestor


@pytest.mark.parametrize("cloud,region", [("aws", "us-east-1"), ("azure", "eastus")])
def test_cross_cloud_governed_mock_release(cloud, region):
    workflow_id = f"acceptance-{cloud}"
    verifier = TokenVerifier(b"local-test-signing-key-with-32-plus-bytes")
    changes = MockChangeService(verifier)
    request = {
        "cloud": cloud, "environment": "sandbox", "requester": "engineer@example.com",
        "application": {"name": "sample-api", "repository": "https://github.com/example/sample-api"},
        "infrastructure": {"region": region, "module": "sandbox-api"},
        "approval": {"required": True},
    }
    plan = build_graph(MockModelGateway()).invoke({"value": WorkflowInput(workflow_id, json.dumps(request))})["plan"]
    change = changes.create(
        tenant="team-a", workflow_id=workflow_id, plan_digest=plan.digest,
        requester=request["requester"], environment="sandbox",
    )
    request["approval"]["change_record"] = change.change_id
    approval = verifier.sign(ApprovalClaims(
        workflow_id=workflow_id, plan_digest=plan.digest, environment="sandbox",
        requester=request["requester"], change_record=change.change_id,
        approver="reviewer@example.com",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    ))
    assert changes.approve(change.change_id, approval, b"CAB reviewed exact plan").status == "approved"

    workspace = Workspace("team-a", cloud, "sandbox", 100)
    tacos = MockTacos(verifier)
    tacos.plan(TacosRun(workspace, workflow_id, plan.digest, request["requester"],
                        change.change_id, 10, "planned"))
    workload = MockWorkloadBroker(verifier).issue(
        tenant="team-a", workflow_id=workflow_id, plan_digest=plan.digest,
    )
    assert tacos.apply(workflow_id, approval, workload).status == "applied"

    attestor = MockAttestor(b"local-test-attestation-key-with-32-bytes")
    materials = b"mock-bill-of-materials"

    def admit(commit_digest: str) -> bool:
        provenance = attestor.attest(
            tenant="team-a", workflow_id=workflow_id, plan_digest=plan.digest,
            source_digest=commit_digest, image_digest=commit_digest,
            materials=materials,
        )
        return attestor.admit(
            provenance, tenant="team-a", workflow_id=workflow_id,
            plan_digest=plan.digest, image_digest=commit_digest,
            materials=materials,
        )

    report = simulate_delivery(ApprovalCheck(plan, json.dumps(request), approval), admission=admit)
    assert report.deployment_status == "healthy"
    assert report.image_ref.endswith(f"@sha256:{report.commit_digest}")
    assert report.security_passed and report.ci_passed and report.supply_chain_passed
