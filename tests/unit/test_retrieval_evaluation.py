from qdrant_client import QdrantClient

from agents.knowledge.agent import EnterpriseKnowledgeAgent
from agents.knowledge.retrieval import ApprovedDocument, KnowledgeIndex
from evaluations.retrieval_quality import score_retrieval


def test_retrieval_regression_gate_and_source_attribution():
    index = KnowledgeIndex(QdrantClient(":memory:"))
    index.approve(ApprovedDocument(
        "repo://docs/aws-vpc.md", "AWS VPC", "private subnet architecture and VPC",
        "team-a", ("planner",), "v1", "owner",
    ))
    result = EnterpriseKnowledgeAgent(index).answer(
        "AWS VPC private subnet", tenant="team-a", roles=("planner",),
    )
    score = score_retrieval([hit.source for hit in result.sources], {"repo://docs/aws-vpc.md"})
    assert score.recall_at_k == score.precision_at_k == score.reciprocal_rank == 1.0
    assert "repo://docs/aws-vpc.md@v1" in result.text
    denied = EnterpriseKnowledgeAgent(index).answer(
        "AWS VPC", tenant="team-b", roles=("planner",),
    )
    assert denied.sources == ()
