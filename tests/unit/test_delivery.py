import json

import pytest

from orchestration.state.contracts import ApprovalCheck, MockPlan
from orchestration.temporal.activities.delivery import simulate_delivery
from security.supply_chain.scanning import blocking, mock_scan, to_sarif


def check():
    request = json.dumps({
        "cloud": "aws", "environment": "sandbox", "requester": "engineer@example.com",
        "application": {"name": "sample-api", "repository": "https://github.com/example/sample-api"},
        "infrastructure": {"region": "us-east-1", "module": "sandbox-api"},
        "approval": {"required": True},
    })
    return ApprovalCheck(MockPlan("w1", "aws", "sandbox", "sample-api", "a" * 64), request, "test-token")


def test_mock_delivery_healthy_and_rollback():
    value = check()
    healthy = simulate_delivery(value, admission=lambda _: True)
    assert healthy.workflow_id == "w1"
    assert healthy.plan_digest == "a" * 64
    assert healthy.image_ref.endswith(f"@sha256:{healthy.commit_digest}")
    assert healthy.ci_passed and healthy.security_passed
    assert healthy.supply_chain_passed
    assert healthy.deployment_status == "healthy"
    rollback = simulate_delivery(value, healthy=False, admission=lambda _: True)
    assert rollback.deployment_status == "rolled_back"
    assert rollback.deployment_revision == "previous"


def test_blocking_scan_prevents_pull_request_and_deployment():
    content = "DEMO_SECRET=unsafe\n"
    findings = mock_scan(content)
    assert blocking(findings)
    sarif = to_sarif(findings)
    assert sarif["version"] == "2.1.0"
    assert len(sarif["runs"]) == 4
    assert sarif["runs"][3]["results"][0]["ruleId"] == "hardcoded-secret"
    with pytest.raises(ValueError, match="blocking security"):
        simulate_delivery(check(), content=content)


def test_invalid_generated_source_cannot_deploy():
    with pytest.raises(SyntaxError):
        simulate_delivery(check(), content="def broken(:\n")


def test_admission_rejection_prevents_deployment():
    with pytest.raises(PermissionError, match="admission denied"):
        simulate_delivery(check(), admission=lambda _: False)


def test_mock_vulnerable_dependency_blocks_delivery():
    with pytest.raises(ValueError, match="blocking security"):
        simulate_delivery(check(), content="VULNERABLE_IMAGE=old\n")


@pytest.mark.parametrize("marker,tool", [
    ("VULNERABLE_IMAGE=old", "trivy-mock"),
    ("PUBLIC_CIDR=0.0.0.0/0", "checkov-mock"),
    ("subprocess.run('echo', shell=True)", "semgrep-mock"),
])
def test_each_mock_scanner_blocks(marker, tool):
    findings = mock_scan(marker)
    assert any(f.tool == tool for f in findings)
    assert blocking(findings)
