from qdrant_client import QdrantClient

from agents.knowledge.retrieval import ApprovedDocument, KnowledgeIndex, create_index
from agents.planning.graph import build_graph
from gateways.llm.model import MockModelGateway
from orchestration.state.contracts import WorkflowInput
from pathlib import Path


def test_approved_knowledge_has_citations_and_tenant_role_filters():
    index = KnowledgeIndex(QdrantClient(":memory:"))
    index.approve(ApprovedDocument(
        "repo://infrastructure/modules/aws/README.md", "AWS VPC module",
        "Approved VPC and private subnet architecture", "team-a", ("engineer",),
        "abc123", "platform-owner",
    ))
    index.approve(ApprovedDocument(
        "repo://security/policies/private.md", "Private security standard",
        "Approved VPC restriction for auditors", "team-a", ("auditor",),
        "def456", "security-owner",
    ))
    index.approve(ApprovedDocument(
        "repo://infrastructure/modules/azure/README.md", "Azure VNet",
        "Approved Azure VNet architecture", "team-b", ("engineer",),
        "ghi789", "platform-owner",
    ))
    hits = index.search("VPC private subnet", tenant="team-a", roles=("engineer",))
    assert len(hits) == 1
    assert hits[0].source.startswith("repo://")
    assert hits[0].revision == "abc123"
    assert index.search("VPC", tenant="team-b", roles=("engineer",))[0].title == "Azure VNet"


def test_unapproved_or_unscoped_knowledge_is_denied():
    index = KnowledgeIndex(QdrantClient(":memory:"))
    try:
        index.approve(ApprovedDocument("file:///tmp/untrusted", "bad", "bad", "a", ("reader",), "v1", "owner"))
    except ValueError:
        pass
    else:
        assert False, "unverified source was accepted"
    try:
        index.search("module", tenant="a", roles=())
    except ValueError:
        pass
    else:
        assert False, "unscoped search was accepted"


def test_planner_binds_source_revision_into_approval_digest():
    index = KnowledgeIndex(QdrantClient(":memory:"))
    request = (Path(__file__).parents[2] / "evaluations/golden_requests/aws-sandbox.json").read_text()
    value = WorkflowInput("workflow-123", request)
    baseline = build_graph(MockModelGateway()).invoke({"value": value})["plan"]
    index.approve(ApprovedDocument(
        "repo://docs/architecture/aws.md", "AWS sandbox", "sandbox-api private network",
        "team-a", ("planner",), "v1", "owner",
    ))
    class RecordingGateway:
        def __init__(self): self.context = ()
        def propose(self, request, *, context=()):
            self.context = context
            return MockModelGateway().propose(request)
    gateway = RecordingGateway()
    cited = build_graph(gateway, knowledge=index, tenant="team-a", roles=("planner",)).invoke({"value": value})["plan"]
    assert cited.sources == ("repo://docs/architecture/aws.md@v1",)
    assert cited.digest != baseline.digest
    assert gateway.context[0].source == "repo://docs/architecture/aws.md"


def test_remote_index_rejects_cleartext_and_missing_credentials():
    for url, key in (("http://example.com:6333", "secret"), ("https://example.com", None)):
        try:
            create_index(url, key)
        except ValueError:
            pass
        else:
            assert False, "insecure remote Qdrant was accepted"
