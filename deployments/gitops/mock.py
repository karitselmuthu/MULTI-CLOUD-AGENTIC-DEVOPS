"""Memory-only GitOps deployment simulation."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Deployment:
    status: str
    revision: str


class MockGitOps:
    def reconcile(self, commit_digest: str, *, healthy: bool = True) -> Deployment:
        if len(commit_digest) != 64:
            raise ValueError("commit digest required")
        return Deployment("healthy" if healthy else "rolled_back", commit_digest if healthy else "previous")

