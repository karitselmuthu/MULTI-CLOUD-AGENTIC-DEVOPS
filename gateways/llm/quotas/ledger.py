"""Atomic in-process estimates; production needs a durable distributed ledger."""

from dataclasses import dataclass
from threading import RLock


class QuotaExceeded(PermissionError):
    pass


@dataclass(frozen=True)
class QuotaPolicy:
    max_calls: int
    max_estimated_cost: float

    def __post_init__(self):
        if self.max_calls < 0 or self.max_estimated_cost < 0:
            raise ValueError("invalid tenant quota")


class TenantQuotaLedger:
    def __init__(self, policies: dict[str, QuotaPolicy]):
        self.policies = policies
        self._used: dict[str, tuple[int, float]] = {}
        self._lock = RLock()

    def reserve(self, tenant: str, estimated_cost: float) -> None:
        with self._lock:
            policy = self.policies.get(tenant)
            if policy is None or estimated_cost < 0:
                raise QuotaExceeded("tenant has no model quota")
            calls, cost = self._used.get(tenant, (0, 0.0))
            if calls + 1 > policy.max_calls or cost + estimated_cost > policy.max_estimated_cost:
                raise QuotaExceeded("tenant model quota exceeded")
            self._used[tenant] = (calls + 1, cost + estimated_cost)

    def release(self, tenant: str, estimated_cost: float) -> None:
        with self._lock:
            calls, cost = self._used[tenant]
            self._used[tenant] = (calls - 1, max(0.0, cost - estimated_cost))

    def usage(self, tenant: str) -> tuple[int, float]:
        with self._lock:
            return self._used.get(tenant, (0, 0.0))
