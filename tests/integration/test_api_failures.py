"""Local API failure paths for queued workflows."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from apps.api.database import Base, WorkflowRecord, utc_now
from apps.api.main import create_app
from orchestration.state.contracts import MockPlan
from security.identity.tokens import ApprovalClaims, TokenVerifier


class FakeHandle:
    def __init__(self, workflow_id: str, *, fail_query: bool = False):
        self.workflow_id = workflow_id
        self.fail_query = fail_query

    async def query(self, method):
        if self.fail_query:
            raise TimeoutError("mock Temporal query timeout")
        if method.__name__ == "get_status":
            return "awaiting_approval"
        return MockPlan(self.workflow_id, "aws", "sandbox", "sample-api", "a" * 64)


class FakeTemporal:
    def __init__(self, *, fail_query: bool = False):
        self.fail_query = fail_query

    def get_workflow_handle(self, workflow_id: str):
        return FakeHandle(workflow_id, fail_query=self.fail_query)


@pytest.fixture
def queued_app(tmp_path):
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'api-failures.db'}")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(engine, expire_on_commit=False)
    workflow_id = str(uuid4())
    request_json = ('{"cloud":"aws","environment":"sandbox","requester":"engineer@example.com",'
                    '"application":{"name":"sample-api","repository":"https://github.com/example/sample-api"},'
                    '"infrastructure":{"region":"us-east-1","module":"sandbox-api"},'
                    '"approval":{"required":true}}')
    with sessions() as session:
        session.add(WorkflowRecord(
            id=workflow_id, idempotency_key="failure-test", request_digest="a" * 64,
            request_json=request_json, cloud="aws", environment="sandbox",
            status="queued", created_at=utc_now(),
        ))
        session.commit()
    yield sessions, workflow_id
    engine.dispose()


def test_temporal_query_timeout_returns_unavailable(queued_app):
    sessions, workflow_id = queued_app
    with TestClient(create_app(sessions, FakeTemporal(fail_query=True))) as client:
        response = client.get(f"/workflows/{workflow_id}")
        assert response.status_code == 503
        assert response.json()["detail"] == "workflow state unavailable"


def test_missing_signing_secret_blocks_approval(queued_app, monkeypatch):
    sessions, workflow_id = queued_app
    valid_token = TokenVerifier(b"local-test-signing-key-with-32-plus-bytes").sign(ApprovalClaims(
        workflow_id=workflow_id, plan_digest="a" * 64, environment="sandbox",
        requester="engineer@example.com", approver="reviewer@example.com",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    ))
    monkeypatch.delenv("AGENT_SIGNING_KEY", raising=False)
    with TestClient(create_app(sessions, FakeTemporal())) as client:
        response = client.post(f"/workflows/{workflow_id}/approve", json={"signed_approval": valid_token})
        assert response.status_code == 403
        assert response.json()["detail"] == "invalid approval"


def test_expired_approval_blocks_signal(queued_app, monkeypatch):
    sessions, workflow_id = queued_app
    secret = b"local-test-signing-key-with-32-plus-bytes"
    monkeypatch.setenv("AGENT_SIGNING_KEY", secret.decode())
    expired = TokenVerifier(secret).sign(ApprovalClaims(
        workflow_id=workflow_id, plan_digest="a" * 64, environment="sandbox",
        requester="engineer@example.com", approver="reviewer@example.com",
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    ))
    with TestClient(create_app(sessions, FakeTemporal())) as client:
        response = client.post(f"/workflows/{workflow_id}/approve", json={"signed_approval": expired})
        assert response.status_code == 403
        assert response.json()["detail"] == "invalid approval"
