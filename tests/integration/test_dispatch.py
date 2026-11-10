import json
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from temporalio.common import WorkflowIDReusePolicy
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from apps.api.database import AuditEvent, Base, WorkflowRecord, utc_now
from orchestration.state.contracts import WorkflowInput
from orchestration.temporal.activities.mock import execute_mock_plan, prepare_mock_plan
from orchestration.temporal.dispatch import TASK_QUEUE, dispatch_once
from orchestration.temporal.workflows.request import RequestWorkflow


@pytest.mark.asyncio
async def test_dispatch_retries_after_start_before_database_commit(tmp_path):
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'dispatch.db'}")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(engine, expire_on_commit=False)
    workflow_id = str(uuid4())
    request_json = json.dumps({
        "cloud": "aws", "environment": "sandbox", "requester": "engineer@example.com",
        "application": {"name": "sample-api", "repository": "https://github.com/example/sample-api"},
        "infrastructure": {"region": "us-east-1", "module": "sandbox-api"},
        "approval": {"required": True},
    })
    with sessions() as session:
        session.add(WorkflowRecord(
            id=workflow_id, idempotency_key="dispatch-test", request_digest="digest",
            request_json=request_json, cloud="aws", environment="sandbox",
            status="received", created_at=utc_now(),
        ))
        session.commit()

    async with await WorkflowEnvironment.start_local() as env:
        async with Worker(
            env.client, task_queue=TASK_QUEUE, workflows=[RequestWorkflow],
            activities=[prepare_mock_plan, execute_mock_plan],
        ):
            # Simulate a crash after Temporal accepts the start and before the DB updates.
            handle = await env.client.start_workflow(
                RequestWorkflow.run,
                WorkflowInput(workflow_id, request_json),
                id=workflow_id, task_queue=TASK_QUEUE,
                id_reuse_policy=WorkflowIDReusePolicy.REJECT_DUPLICATE,
            )
            assert await dispatch_once(env.client, sessions) == 1
            assert await dispatch_once(env.client, sessions) == 0
            with sessions() as session:
                assert session.get(WorkflowRecord, workflow_id).status == "queued"
                assert [e.event_type for e in session.scalars(select(AuditEvent)).all()] == ["workflow.dispatched"]
            plan = None
            for _ in range(100):
                plan = await handle.query(RequestWorkflow.get_plan)
                if plan:
                    break
            assert plan is not None
            await handle.signal(RequestWorkflow.approve, plan.digest)
            assert (await handle.result()).startswith("simulated:")
    engine.dispose()
