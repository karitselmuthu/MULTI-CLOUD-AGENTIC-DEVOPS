"""Local tenant policy bundle and namespace reservation."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TenantPolicy:
    tenant: str
    namespace: str
    allowed_clouds: frozenset[str]
    budget_limit: int


class TenantRegistry:
    def __init__(self):
        self._policies: dict[str, TenantPolicy] = {}

    def register(self, policy: TenantPolicy) -> None:
        if not policy.tenant or not policy.namespace or policy.budget_limit <= 0:
            raise ValueError("tenant, namespace, and positive budget are required")
        if policy.tenant in self._policies:
            raise ValueError("tenant already registered")
        if any(existing.namespace == policy.namespace for existing in self._policies.values()):
            raise ValueError("namespace already assigned")
        self._policies[policy.tenant] = policy

    def authorize(self, *, tenant: str, cloud: str, environment: str,
                  estimated_cost: int) -> TenantPolicy:
        policy = self._policies[tenant]
        if cloud not in policy.allowed_clouds or environment != "sandbox":
            raise PermissionError("tenant target not allowed")
        if estimated_cost < 0 or estimated_cost > policy.budget_limit:
            raise PermissionError("tenant budget exceeded")
        return policy
