"""Mock-only activities; no cloud or repository mutation.

Source: https://docs.temporal.io/develop/python/activities/basics
"""

import os
from datetime import datetime, timedelta, timezone

from temporalio import activity

from orchestration.state.contracts import ApprovalCheck, MockPlan, WorkflowInput
from agents.planning.graph import build_graph
from gateways.llm.model import MockModelGateway
from apps.api.contracts import RequestCreate
from gateways.mcp.gateway import MCPGateway, OpaPolicy, ToolContext, approval_matches
from security.identity.tokens import AgentClaims, ApprovalClaims, TokenVerifier


@activity.defn
async def prepare_mock_plan(value: WorkflowInput) -> MockPlan:
    return build_graph(MockModelGateway()).invoke({"value": value})["plan"]


def _context(value: ApprovalCheck) -> ToolContext:
    request = RequestCreate.model_validate_json(value.request_json)
    return ToolContext(
        workflow_id=value.plan.workflow_id,
        plan_digest=value.plan.digest,
        environment=request.environment.value,
        requester=request.requester,
        change_record=request.approval.change_record,
    )


def _verifier() -> TokenVerifier:
    secret = os.environ.get("AGENT_SIGNING_KEY", "").encode()
    return TokenVerifier(secret)


@activity.defn
async def verify_mock_approval(value: ApprovalCheck) -> bool:
    verifier = _verifier()
    try:
        approval = verifier.verify(value.approval_token, ApprovalClaims)
    except PermissionError:
        return False
    return approval_matches(approval, _context(value))


@activity.defn
async def execute_mock_plan(value: ApprovalCheck) -> str:
    verifier = _verifier()
    agent_token = verifier.sign(AgentClaims(
        role="devops", workflow_id=value.plan.workflow_id,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    ))
    MCPGateway(verifier, OpaPolicy()).call(
        agent_token, "mock.execute", _context(value), value.approval_token
    )
    return f"simulated:{value.plan.workflow_id}:{value.plan.digest}"
