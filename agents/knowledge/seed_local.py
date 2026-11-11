"""Seed repository documents as explicitly labeled local knowledge fixtures."""

import os
import subprocess
from pathlib import Path

from agents.knowledge.retrieval import create_index
from knowledge.ingestion import ApprovedSource, RepositoryIngestor


FIXTURES = (
    "infrastructure/modules/aws/README.md",
    "infrastructure/modules/azure/README.md",
    "docs/architecture/cloud-sandbox-standard.md",
    "docs/governance/security-policy-reference.md",
    "docs/runbooks/local-workflow-recovery.md",
)


def main() -> None:
    url = os.environ.get("QDRANT_URL")
    key = os.environ.get("QDRANT_API_KEY")
    tenant = os.environ.get("KNOWLEDGE_TENANT")
    if not url or not key or not tenant:
        raise SystemExit("QDRANT_URL, QDRANT_API_KEY and KNOWLEDGE_TENANT are required")
    root = Path(__file__).resolve().parents[2]
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    index = create_index(url, key, create=True)
    ingestor = RepositoryIngestor(root, index, FIXTURES)
    for relative in FIXTURES:
        ingestor.ingest(ApprovedSource(
            path=relative, tenant=tenant,
            roles=("planner", "engineer"), revision=revision,
            approved_by="local-fixture-only",
        ))
    print(f"Indexed {len(FIXTURES)} local fixtures for {tenant} at {revision}")


if __name__ == "__main__":
    main()
