"""Repository automation contract and memory-only implementation.

GitHub PR API reference: https://docs.github.com/en/rest/pulls/pulls#create-a-pull-request
"""

import hashlib
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class PullRequest:
    branch: str
    url: str
    commit_digest: str


class RepositoryAdapter(Protocol):
    def propose(self, repository: str, workflow_id: str, content: str) -> PullRequest: ...


class MockRepositoryAdapter:
    def propose(self, repository: str, workflow_id: str, content: str) -> PullRequest:
        if not repository.startswith("https://github.com/") and not repository.startswith("https://dev.azure.com/"):
            raise ValueError("unsupported mock repository URL")
        branch = f"agent/{workflow_id}"
        digest = hashlib.sha256(content.encode()).hexdigest()
        return PullRequest(branch, f"mock://pull-request/{workflow_id}", digest)

