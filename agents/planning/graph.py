"""Structured, mock-only LangGraph planner.

Source: https://docs.langchain.com/oss/python/langgraph/graph-api
"""

import hashlib
import json
from typing import TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, ConfigDict
from typing import Literal

from apps.api.contracts import Cloud, Environment, RequestCreate
from agents.shared.tools import MockModuleCatalog, ModuleCatalog
from gateways.llm.model import ModelGateway
from orchestration.state.contracts import MockPlan, WorkflowInput


class PlanProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cloud: Cloud
    environment: Environment
    application: str
    action: Literal["simulate"]


class PlanningState(TypedDict, total=False):
    value: WorkflowInput
    request: RequestCreate
    proposal: PlanProposal
    plan: MockPlan


def build_graph(gateway: ModelGateway, catalog: ModuleCatalog | None = None):
    catalog = catalog or MockModuleCatalog()

    def validate_request(state: PlanningState) -> dict:
        request = RequestCreate.model_validate_json(state["value"].request_json)
        return {"request": request}

    def propose(state: PlanningState) -> dict:
        raw = gateway.propose(state["request"])
        proposal = PlanProposal.model_validate(raw)
        if proposal.cloud != state["request"].cloud or proposal.environment != state["request"].environment:
            raise ValueError("model proposal changed the approved target")
        if proposal.application != state["request"].application.name:
            raise ValueError("model proposal changed the application")
        return {"proposal": proposal}

    def check_module(state: PlanningState) -> dict:
        request = state["request"]
        if not catalog.supports(request.cloud, request.infrastructure.module):
            raise ValueError("unsupported module for cloud")
        return {}

    def finalize(state: PlanningState) -> dict:
        proposal = state["proposal"]
        canonical = json.dumps(
            {"workflow_id": state["value"].workflow_id, **proposal.model_dump(mode="json")},
            sort_keys=True, separators=(",", ":"),
        )
        plan = MockPlan(
            workflow_id=state["value"].workflow_id,
            cloud=proposal.cloud.value,
            environment=proposal.environment.value,
            application=proposal.application,
            digest=hashlib.sha256(canonical.encode()).hexdigest(),
        )
        return {"plan": plan}

    graph = StateGraph(PlanningState)
    graph.add_node("validate_request", validate_request)
    graph.add_node("check_module", check_module)
    graph.add_node("propose", propose)
    graph.add_node("finalize", finalize)
    graph.add_edge(START, "validate_request")
    graph.add_edge("validate_request", "check_module")
    graph.add_edge("check_module", "propose")
    graph.add_edge("propose", "finalize")
    graph.add_edge("finalize", END)
    return graph.compile()
