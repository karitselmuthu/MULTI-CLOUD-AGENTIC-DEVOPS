"""Local canary and rollback state machine."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RolloutResult:
    status: str
    active_revision: str
    canary_percent: int


class MockCanaryRollout:
    def release(self, *, previous_revision: str, candidate_revision: str,
                canary_healthy: bool, full_healthy: bool) -> RolloutResult:
        if not previous_revision or not candidate_revision or previous_revision == candidate_revision:
            raise ValueError("distinct revisions are required")
        if not canary_healthy:
            return RolloutResult("rolled_back", previous_revision, 10)
        if not full_healthy:
            return RolloutResult("rolled_back", previous_revision, 100)
        return RolloutResult("healthy", candidate_revision, 100)
