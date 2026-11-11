from pathlib import Path

import pytest
from qdrant_client import QdrantClient

from knowledge.chunking import chunk_markdown
from knowledge.ingestion import ApprovedSource, RepositoryIngestor
from knowledge.retrieval.qdrant import ApprovedDocument, KnowledgeIndex


def test_chunk_policy_bounds_content_and_keeps_heading():
    chunks = chunk_markdown("# Network\n" + "private subnet " * 150, size=200, overlap=20)
    assert len(chunks) > 1
    assert all(len(chunk.text) <= 200 for chunk in chunks)
    assert chunks[0].heading == "Network"
    assert chunks[1].heading == "Network"
    assert chunks[1].start == chunks[0].end - 20


def test_repository_ingestion_rejects_traversal_and_replaces_old_chunks(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "module.md").write_text("# Module\n" + "private subnet " * 100)
    index = KnowledgeIndex(QdrantClient(":memory:"))
    ingestor = RepositoryIngestor(root, index, ("module.md", "../outside.md"))
    ingestor.ingest(ApprovedSource("module.md", "team-a", ("planner",), "v1", "owner"))
    first = index.search("private subnet", tenant="team-a", roles=("planner",))
    assert len(first) == 1 and first[0].revision == "v1"
    (root / "module.md").write_text("# Module\nnew module")
    ingestor.ingest(ApprovedSource("module.md", "team-a", ("planner",), "v2", "owner"))
    assert [hit.revision for hit in index.search("module", tenant="team-a", roles=("planner",))] == ["v2"]
    with pytest.raises(ValueError, match="repository Markdown"):
        ingestor.ingest(ApprovedSource("../outside.md", "team-a", ("planner",), "v2", "owner"))
    with pytest.raises(PermissionError, match="allowlisted"):
        ingestor.ingest(ApprovedSource("other.md", "team-a", ("planner",), "v2", "owner"))


def test_failed_reapproval_preserves_previous_document(monkeypatch):
    index = KnowledgeIndex(QdrantClient(":memory:"))
    document = ApprovedDocument("repo://module.md", "Module", "private subnet", "team-a",
                                ("planner",), "v1", "owner")
    index.approve(document)

    def fail_upload(*args, **kwargs):
        raise RuntimeError("upload failed")

    monkeypatch.setattr(index.client, "upsert", fail_upload)
    with pytest.raises(RuntimeError, match="upload failed"):
        index.approve(ApprovedDocument("repo://module.md", "Module", "public network", "team-a",
                                       ("planner",), "v2", "owner"))
    assert [hit.revision for hit in index.search("private subnet", tenant="team-a", roles=("planner",))] == ["v1"]
