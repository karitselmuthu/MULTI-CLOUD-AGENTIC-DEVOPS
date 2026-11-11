from dataclasses import replace

from evaluations.deployment import deployment_passes
from evaluations.security import security_passes
from evaluations.workflow_reliability import workflow_reliability_passes
from orchestration.state.delivery import DeliveryReport


def test_deployment_security_and_workflow_gates_are_independent():
    report = DeliveryReport(
        workflow_id="w", plan_digest="d", branch="b", pull_request="p",
        commit_digest="f" * 64, image_ref="repo@sha256:" + "f" * 64,
        ci_passed=True, security_passed=True, supply_chain_passed=True,
        deployment_status="healthy", deployment_revision="rev-1",
    )
    events = ["request.received", "workflow.dispatched", "approval.signaled"]
    assert deployment_passes(report)
    assert security_passes(report)
    assert workflow_reliability_passes("completed", events)
    assert not deployment_passes(replace(report, deployment_status="failed"))
    assert security_passes(replace(report, deployment_status="failed"))
    assert not security_passes(replace(report, supply_chain_passed=False))
    assert not workflow_reliability_passes("completed", events[:-1])
