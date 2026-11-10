from datetime import datetime, timedelta, timezone
from pathlib import Path
import os
import shutil

import pytest

from gateways.mcp.gateway import MCPGateway, OpaPolicy, ToolContext
from security.identity.tokens import AgentClaims, ApprovalClaims, TokenVerifier


def make_verifier():
    return TokenVerifier(b"local-test-signing-key-with-32-plus-bytes")


def expiry(minutes=5):
    return datetime.now(timezone.utc) + timedelta(minutes=minutes)


def test_token_rejects_tampering_expiry_and_wrong_kind():
    verifier = make_verifier()
    token = verifier.sign(AgentClaims(role="planning", workflow_id="w1", expires_at=expiry()))
    assert verifier.verify(token, AgentClaims).workflow_id == "w1"
    with pytest.raises(PermissionError):
        verifier.verify(token + "bad", AgentClaims)
    with pytest.raises(PermissionError):
        verifier.verify("%%%.$$$", AgentClaims)
    with pytest.raises(PermissionError):
        verifier.verify(token, ApprovalClaims)
    expired = verifier.sign(AgentClaims(role="planning", workflow_id="w1", expires_at=expiry(-1)))
    with pytest.raises(PermissionError):
        verifier.verify(expired, AgentClaims)


def test_opa_unavailable_denies():
    policy = OpaPolicy(binary="/nonexistent/opa")
    assert not policy.allows({"agent": {"role": "planning", "workflow_id": "w1"}, "workflow_id": "w1", "tool": "catalog.read"})


def test_gateway_approval_binding_and_permissions():
    binary = os.getenv("OPA_BIN") or shutil.which("opa")
    if not binary or not Path(binary).is_file():
        pytest.skip("OPA CLI unavailable; set OPA_BIN to run policy integration test")
    verifier = make_verifier()
    gateway = MCPGateway(verifier, OpaPolicy(binary=binary))
    digest = "a" * 64
    context = ToolContext("w1", digest, "sandbox", "engineer@example.com", "CR-123")
    planning = verifier.sign(AgentClaims(role="planning", workflow_id="w1", expires_at=expiry()))
    devops = verifier.sign(AgentClaims(role="devops", workflow_id="w1", expires_at=expiry()))
    approval = verifier.sign(ApprovalClaims(
        workflow_id="w1", plan_digest=digest, environment="sandbox",
        requester="engineer@example.com", change_record="CR-123",
        approver="reviewer@example.com", expires_at=expiry(),
    ))

    assert gateway.call(planning, "catalog.read", context) == {"modules": ["sandbox-api"]}
    with pytest.raises(PermissionError):
        gateway.call(planning, "mock.execute", context, approval)
    with pytest.raises(PermissionError):
        gateway.call(devops, "mock.execute", context)
    with pytest.raises(PermissionError):
        gateway.call(devops, "mock.execute", ToolContext("w1", "b" * 64, "sandbox", "engineer@example.com", "CR-123"), approval)
    with pytest.raises(PermissionError):
        gateway.call(devops, "mock.execute", ToolContext("w1", digest, "prod", "engineer@example.com", "CR-123"), approval)
    with pytest.raises(PermissionError):
        gateway.call(devops, "mock.execute", ToolContext("w2", digest, "sandbox", "engineer@example.com", "CR-123"), approval)
    assert gateway.call(devops, "mock.execute", context, approval)["status"] == "simulated"
