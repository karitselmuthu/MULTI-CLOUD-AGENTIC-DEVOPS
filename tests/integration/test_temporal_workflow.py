import asyncio
import json
from uuid import uuid4

import pytest
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker
from temporalio import activity
from temporalio.client import WorkflowFailureError

from orchestration.state.contracts import WorkflowInput
from orchestration.temporal.activities.mock import execute_mock_plan, prepare_mock_plan
from orchestration.temporal.workflows.request import RequestWorkflow


async def wait_for_status(handle, expected):
    for _ in range(100):
        if await handle.query(RequestWorkflow.get_status) == expected:
            return
        await asyncio.sleep(0.05)
    raise AssertionError(f"workflow did not reach {expected}")


@pytest.mark.asyncio
async def test_approval_digest_and_worker_restart():
    workflow_id = str(uuid4())
    value = WorkflowInput(
        workflow_id=workflow_id,
        request_json=json.dumps({"cloud": "aws", "environment": "sandbox", "application": {"name": "sample-api"}}),
    )
    queue = str(uuid4())
    async with await WorkflowEnvironment.start_local() as env:
        async with Worker(
            env.client, task_queue=queue, workflows=[RequestWorkflow],
            activities=[prepare_mock_plan, execute_mock_plan],
        ):
            handle = await env.client.start_workflow(RequestWorkflow.run, value, id=workflow_id, task_queue=queue)
            await wait_for_status(handle, "awaiting_approval")
            plan = await handle.query(RequestWorkflow.get_plan)
            await handle.signal(RequestWorkflow.approve, "incorrect-digest")
            assert await handle.query(RequestWorkflow.get_status) == "awaiting_approval"

        async with Worker(
            env.client, task_queue=queue, workflows=[RequestWorkflow],
            activities=[prepare_mock_plan, execute_mock_plan],
        ):
            await handle.signal(RequestWorkflow.approve, plan.digest)
            assert await handle.result() == f"simulated:{workflow_id}:{plan.digest}"
            assert await handle.query(RequestWorkflow.get_status) == "completed"


@pytest.mark.asyncio
async def test_approval_timeout_without_execution():
    workflow_id = str(uuid4())
    value = WorkflowInput(
        workflow_id=workflow_id,
        request_json=json.dumps({"cloud": "azure", "environment": "dev", "application": {"name": "sample-api"}}),
    )
    queue = str(uuid4())
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(
            env.client, task_queue=queue, workflows=[RequestWorkflow],
            activities=[prepare_mock_plan, execute_mock_plan],
        ):
            handle = await env.client.start_workflow(RequestWorkflow.run, value, id=workflow_id, task_queue=queue)
            assert await handle.result() == "approval_expired"


@pytest.mark.asyncio
async def test_activity_retry_and_cancellation():
    attempts = 0

    @activity.defn(name="prepare_mock_plan")
    async def flaky_plan(value: WorkflowInput):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("temporary planner failure")
        return await prepare_mock_plan(value)

    queue = str(uuid4())
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(
            env.client, task_queue=queue, workflows=[RequestWorkflow],
            activities=[flaky_plan, execute_mock_plan],
        ):
            workflow_id = str(uuid4())
            value = WorkflowInput(
                workflow_id,
                json.dumps({"cloud": "aws", "environment": "dev", "application": {"name": "sample-api"}}),
            )
            handle = await env.client.start_workflow(RequestWorkflow.run, value, id=workflow_id, task_queue=queue)
            await wait_for_status(handle, "awaiting_approval")
            assert attempts == 2
            await handle.cancel()
            with pytest.raises(WorkflowFailureError):
                await handle.result()
