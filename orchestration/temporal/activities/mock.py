"""Mock-only activities; no cloud or repository mutation.

Source: https://docs.temporal.io/develop/python/activities/basics
"""

from temporalio import activity

from orchestration.state.contracts import MockPlan, WorkflowInput
from agents.planning.graph import build_graph
from gateways.llm.model import MockModelGateway


@activity.defn
async def prepare_mock_plan(value: WorkflowInput) -> MockPlan:
    return build_graph(MockModelGateway()).invoke({"value": value})["plan"]


@activity.defn
async def execute_mock_plan(plan: MockPlan) -> str:
    return f"simulated:{plan.workflow_id}:{plan.digest}"
