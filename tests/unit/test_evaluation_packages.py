import json
from pathlib import Path

from qdrant_client import QdrantClient

from agents.knowledge.agent import EnterpriseKnowledgeAgent
from agents.planning.graph import build_graph
from evaluations.context_quality import citations_are_grounded
from evaluations.model_routing import policy_compliance
from evaluations.rag import evaluate_retrieval_case
from gateways.llm.model import MockModelGateway, ModelRequirements, ProviderProfile
from knowledge.ingestion import ApprovedSource, RepositoryIngestor
from knowledge.retrieval.qdrant import ApprovedDocument, KnowledgeIndex
from orchestration.state.contracts import WorkflowInput


ROOT = Path(__file__).parents[2]


def test_rag_fixtures_cover_module_and_runbook_sources():
    index = KnowledgeIndex(QdrantClient(":memory:"))
    fixtures = json.loads((ROOT / "evaluations/rag/fixtures.json").read_text())
    ingestor = RepositoryIngestor(ROOT, index,
                                  (item["source"].removeprefix("repo://") for item in fixtures))
    for item in fixtures:
        ingestor.ingest(ApprovedSource(item["source"].removeprefix("repo://"),
                                       "team-a", ("planner",), "v1", "fixture"))
    for item in fixtures:
        score = evaluate_retrieval_case(index, item["query"], {item["source"]},
                                        "team-a", ("planner",))
        assert score.recall_at_k == 1.0


def test_context_citations_and_injected_document_do_not_change_target():
    index = KnowledgeIndex(QdrantClient(":memory:"))
    fixture = json.loads((ROOT / "evaluations/context_quality/injection_fixture.json").read_text())
    index.approve(ApprovedDocument(fixture["source"], "Sandbox module", fixture["text"],
                                   "team-a", ("planner",), "v1", "fixture"))
    answer = EnterpriseKnowledgeAgent(index).answer("Sandbox module", tenant="team-a", roles=("planner",))
    assert citations_are_grounded(answer)
    request = (ROOT / "evaluations/golden_requests/aws-sandbox.json").read_text()
    plan = build_graph(MockModelGateway(), knowledge=index, tenant="team-a", roles=("planner",)).invoke({
        "value": WorkflowInput("workflow-123", request),
    })["plan"]
    assert (plan.cloud, plan.environment) == (fixture["expected_cloud"], fixture["expected_environment"])


def test_routing_policy_evaluation_is_separate_from_fallback():
    requirements = ModelRequirements(min_reasoning=3, residency="eu")
    assert policy_compliance(ProviderProfile("eu", 3, 300, 1, frozenset({"eu"})), requirements)
    assert not policy_compliance(ProviderProfile("us", 3, 300, 1, frozenset({"us"})), requirements)
