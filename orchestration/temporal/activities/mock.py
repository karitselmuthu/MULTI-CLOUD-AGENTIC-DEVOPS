"""Mock-only activities; no cloud or repository mutation.

Source: https://docs.temporal.io/develop/python/activities/basics
"""

import hashlib
import json

from temporalio import activity

from orchestration.state.contracts import MockPlan, WorkflowInput


@activity.defn
async def prepare_mock_plan(value: WorkflowInput) -> MockPlan:
    request = json.loads(value.request_json)
    summary = {
        "workflow_id": value.workflow_id,
        "cloud": request["cloud"],
        "environment": request["environment"],
        "application": request["application"]["name"],
    }
    canonical = json.dumps(summary, sort_keys=True, separators=(",", ":"))
    return MockPlan(**summary, digest=hashlib.sha256(canonical.encode()).hexdigest())


@activity.defn
async def execute_mock_plan(plan: MockPlan) -> str:
    return f"simulated:{plan.workflow_id}:{plan.digest}"
