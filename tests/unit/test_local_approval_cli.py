from datetime import datetime, timedelta, timezone
from uuid import uuid4

import httpx
import pytest

from apps.cli.local_approval import issue_from_detail, load_detail, validate_local_url
from apps.cli.local_env import create_local_env
from security.identity.tokens import ApprovalClaims, TokenVerifier


KEY = "local-test-signing-key-with-32-plus-bytes"


@pytest.mark.parametrize("cloud,region", [("aws", "us-east-1"), ("azure", "eastus")])
def test_approval_issuer_binds_both_cloud_plans(cloud, region):
    workflow_id = str(uuid4())
    digest = "a" * 64
    detail = {
        "workflow": {"id": workflow_id, "status": "awaiting_approval", "cloud": cloud,
                     "environment": "sandbox", "plan_digest": digest,
                     "created_at": datetime.now(timezone.utc).isoformat(), "request_digest": "b" * 64},
        "request": {"cloud": cloud, "environment": "sandbox", "requester": "engineer@example.com",
                    "application": {"name": "sample-api", "repository": "https://github.com/example/sample-api"},
                    "infrastructure": {"region": region, "module": "sandbox-api"},
                    "approval": {"required": True, "change_record": "CR-123"}},
        "plan": {"digest": digest},
    }
    token = issue_from_detail(detail, "reviewer@example.com", KEY)
    claims = TokenVerifier(KEY.encode()).verify(token, ApprovalClaims)
    assert claims.workflow_id == workflow_id
    assert claims.plan_digest == digest
    assert claims.requester == "engineer@example.com"
    assert claims.change_record == "CR-123"
    assert claims.expires_at - datetime.now(timezone.utc) <= timedelta(minutes=10)


def test_issuer_rejects_self_approval_stale_plan_and_wrong_state():
    detail = {
        "workflow": {"id": str(uuid4()), "status": "awaiting_approval", "cloud": "aws",
                     "environment": "sandbox", "plan_digest": "a" * 64,
                     "created_at": datetime.now(timezone.utc).isoformat(), "request_digest": "b" * 64},
        "request": {"cloud": "aws", "environment": "sandbox", "requester": "engineer@example.com",
                    "application": {"name": "sample-api", "repository": "https://github.com/example/sample-api"},
                    "infrastructure": {"region": "us-east-1", "module": "sandbox-api"},
                    "approval": {"required": True, "change_record": None}},
        "plan": {"digest": "a" * 64},
    }
    with pytest.raises(ValueError, match="separate approver"):
        issue_from_detail(detail, "engineer@example.com", KEY)
    detail["plan"]["digest"] = "b" * 64
    with pytest.raises(ValueError, match="plan digest"):
        issue_from_detail(detail, "reviewer@example.com", KEY)
    detail["plan"]["digest"] = "a" * 64
    detail["workflow"]["status"] = "completed"
    with pytest.raises(ValueError, match="awaiting approval"):
        issue_from_detail(detail, "reviewer@example.com", KEY)


def test_issuer_uses_only_loopback_and_scoped_dashboard_detail():
    with pytest.raises(ValueError, match="loopback"):
        validate_local_url("https://example.com")
    workflow_id = str(uuid4())

    def respond(request: httpx.Request) -> httpx.Response:
        assert request.url.path == f"/dashboard/workflows/{workflow_id}"
        assert request.headers["Authorization"] == "Bearer local-token"
        return httpx.Response(200, json={"workflow": {"id": workflow_id}})

    with httpx.Client(base_url="http://127.0.0.1:8000", transport=httpx.MockTransport(respond)) as client:
        assert load_detail(client, workflow_id, "local-token")["workflow"]["id"] == workflow_id


def test_local_env_is_private_and_does_not_overwrite(tmp_path):
    path = tmp_path / ".env"
    create_local_env(path, "engineer@example.com")
    content = path.read_text()
    assert "LOCAL_DASHBOARD_TOKEN=" in content
    assert "AGENT_SIGNING_KEY=" in content
    assert "LOCAL_MOCK_APPROVAL_ENABLED=1" in content
    assert path.stat().st_mode & 0o077 == 0
    with pytest.raises(FileExistsError):
        create_local_env(path, "engineer@example.com")
    assert path.read_text() == content
