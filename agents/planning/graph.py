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
from agents.knowledge.retrieval import KnowledgeHit, KnowledgeIndex
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
    sources: tuple[str, ...]
    knowledge_hits: tuple[KnowledgeHit, ...]


def build_graph(gateway: ModelGateway, catalog: ModuleCatalog | None = None,
                knowledge: KnowledgeIndex | None = None, tenant: str | None = None,
                roles: tuple[str, ...] = ()):
    catalog = catalog or MockModuleCatalog()

    def validate_request(state: PlanningState) -> dict:
        request = RequestCreate.model_validate_json(state["value"].request_json)
        return {"request": request}

    def propose(state: PlanningState) -> dict:
        if state["knowledge_hits"]:
            raw = gateway.propose(state["request"], context=state["knowledge_hits"])
        else:
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

    def retrieve_knowledge(state: PlanningState) -> dict:
        if knowledge is None:
            return {"sources": (), "knowledge_hits": ()}
        if not tenant or not roles:
            raise ValueError("knowledge retrieval needs explicit tenant and roles")
        request = state["request"]
        query = f"{request.cloud.value} {request.infrastructure.module} {request.infrastructure.region} security runbook"
        hits = knowledge.search(query, tenant=tenant, roles=roles)
        return {"sources": tuple(f"{hit.source}@{hit.revision}" for hit in hits),
                "knowledge_hits": tuple(hits)}

    def finalize(state: PlanningState) -> dict:
        proposal = state["proposal"]
        canonical = json.dumps(
            {"workflow_id": state["value"].workflow_id, **proposal.model_dump(mode="json"),
             "sources": state["sources"]},
            sort_keys=True, separators=(",", ":"),
        )
        plan = MockPlan(
            workflow_id=state["value"].workflow_id,
            cloud=proposal.cloud.value,
            environment=proposal.environment.value,
            application=proposal.application,
            digest=hashlib.sha256(canonical.encode()).hexdigest(),
            sources=state["sources"],
        )
        return {"plan": plan}

    graph = StateGraph(PlanningState)
    graph.add_node("validate_request", validate_request)
    graph.add_node("check_module", check_module)
    graph.add_node("retrieve_knowledge", retrieve_knowledge)
    graph.add_node("propose", propose)
    graph.add_node("finalize", finalize)
    graph.add_edge(START, "validate_request")
    graph.add_edge("validate_request", "check_module")
    graph.add_edge("check_module", "retrieve_knowledge")
    graph.add_edge("retrieve_knowledge", "propose")
    graph.add_edge("propose", "finalize")
    graph.add_edge("finalize", END)
    return graph.compile()
