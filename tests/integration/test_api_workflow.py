import asyncio
import os
import shutil
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from apps.api.database import AuditEvent, Base
from apps.api.main import create_app
from orchestration.temporal.activities.mock import execute_mock_plan, prepare_mock_plan, verify_mock_approval
from orchestration.temporal.activities.delivery import deliver_mock_plan
from orchestration.temporal.dispatch import TASK_QUEUE, dispatch_once
from orchestration.temporal.workflows.request import RequestWorkflow
from security.identity.tokens import ApprovalClaims, TokenVerifier


@pytest.mark.asyncio
@pytest.mark.parametrize("cloud,region", [("aws", "us-east-1"), ("azure", "eastus")])
async def test_api_request_to_signed_mock_approval(tmp_path, monkeypatch, cloud, region):
    binary = os.getenv("OPA_BIN") or shutil.which("opa")
    if not binary or not Path(binary).is_file():
        pytest.skip("OPA CLI unavailable; set OPA_BIN")
    secret = "local-test-signing-key-with-32-plus-bytes"
    monkeypatch.setenv("AGENT_SIGNING_KEY", secret)
    monkeypatch.setenv("LOCAL_DASHBOARD_TOKEN", "local-dashboard-test-token")
    monkeypatch.setenv("LOCAL_DASHBOARD_REQUESTER", "engineer@example.com")
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'api-workflow.db'}")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(engine, expire_on_commit=False)
    request = {
        "cloud": cloud, "environment": "sandbox", "requester": "engineer@example.com",
        "application": {"name": "sample-api", "repository": "https://github.com/example/sample-api"},
        "infrastructure": {"region": region, "module": "sandbox-api"},
        "approval": {"required": True, "change_record": "CR-123"},
    }
    async with await WorkflowEnvironment.start_local(dev_server_existing_path=shutil.which("temporal")) as env:
        async with Worker(
            env.client, task_queue=TASK_QUEUE, workflows=[RequestWorkflow],
            activities=[prepare_mock_plan, verify_mock_approval, execute_mock_plan, deliver_mock_plan],
        ):
            transport = httpx.ASGITransport(app=create_app(sessions, env.client))
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
                created = await http.post("/requests", json=request, headers={"Idempotency-Key": str(uuid4())})
                assert created.status_code == 202
                workflow_id = created.json()["id"]
                assert await dispatch_once(env.client, sessions) == 1
                for _ in range(100):
                    state = (await http.get(f"/workflows/{workflow_id}")).json()
                    if state["status"] == "awaiting_approval":
                        break
                    await asyncio.sleep(0.05)
                assert state["status"] == "awaiting_approval"
                assert len(state["plan_digest"]) == 64
                assert (await http.post(
                    f"/workflows/{workflow_id}/approve",
                    json={"signed_approval": "forged"},
                )).status_code == 403
                dashboard_before = await http.get(
                    f"/dashboard/workflows/{workflow_id}",
                    headers={"Authorization": "Bearer local-dashboard-test-token"},
                )
                assert dashboard_before.status_code == 200
                mock_url = f"/dashboard/workflows/{workflow_id}/local-mock-approval"
                assert (await http.post(mock_url, headers={
                    "Authorization": "Bearer local-dashboard-test-token"
                })).status_code == 403
                monkeypatch.setenv("LOCAL_MOCK_APPROVAL_ENABLED", "1")
                assert (await http.post(mock_url)).status_code == 403
                monkeypatch.setenv("LOCAL_DASHBOARD_REQUESTER", "other-team@example.com")
                assert (await http.post(mock_url, headers={
                    "Authorization": "Bearer local-dashboard-test-token"
                })).status_code == 404
                monkeypatch.setenv("LOCAL_DASHBOARD_REQUESTER", "engineer@example.com")
                issued = await http.post(mock_url, headers={
                    "Authorization": "Bearer local-dashboard-test-token"
                })
                assert issued.status_code == 200
                assert issued.headers["cache-control"] == "no-store"
                token = issued.json()["signed_approval"]
                claims = TokenVerifier(secret.encode()).verify(token, ApprovalClaims)
                assert claims.workflow_id == workflow_id
                assert claims.plan_digest == state["plan_digest"]
                assert claims.approver == "local-mock-reviewer"
                approved = await http.post(
                    f"/workflows/{workflow_id}/approve", json={"signed_approval": token}
                )
                assert approved.status_code == 202
                handle = env.client.get_workflow_handle(workflow_id)
                assert (await handle.result()).startswith("simulated:")
                assert (await http.get(f"/workflows/{workflow_id}")).json()["status"] == "completed"
                assert (await http.post(mock_url, headers={
                    "Authorization": "Bearer local-dashboard-test-token"
                })).status_code == 409
                report = await http.get(f"/workflows/{workflow_id}/report")
                assert report.status_code == 200
                assert report.json()["deployment_status"] == "healthy"
                assert report.json()["supply_chain_passed"] is True
                assert report.json()["image_ref"].endswith(
                    f"@sha256:{report.json()['commit_digest']}"
                )
                dashboard = await http.get(
                    f"/dashboard/workflows/{workflow_id}",
                    headers={"Authorization": "Bearer local-dashboard-test-token"},
                )
                assert dashboard.status_code == 200
                assert dashboard.json()["plan"]["digest"] == state["plan_digest"]
                assert dashboard.json()["report"]["deployment_status"] == "healthy"
                with sessions() as session:
                    assert [event.event_type for event in session.scalars(select(AuditEvent)).all()] == [
                        "request.received", "workflow.dispatched", "approval.signaled"
                    ]
    engine.dispose()
