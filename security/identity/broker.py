"""Short-lived local workload token issuer; no cloud secret exchange.

HMAC reference: https://docs.python.org/3/library/hmac.html
"""

from datetime import datetime, timedelta, timezone

from security.identity.tokens import TokenVerifier, WorkloadClaims


class MockWorkloadBroker:
    def __init__(self, verifier: TokenVerifier):
        self._verifier = verifier

    def issue(self, *, tenant: str, workflow_id: str, plan_digest: str,
              lifetime: timedelta = timedelta(minutes=5)) -> str:
        if lifetime <= timedelta() or lifetime > timedelta(minutes=5):
            raise ValueError("mock workload tokens must live no longer than five minutes")
        claims = WorkloadClaims(
            tenant=tenant, role="tacos-executor", workflow_id=workflow_id,
            plan_digest=plan_digest,
            expires_at=datetime.now(timezone.utc) + lifetime,
        )
        return self._verifier.sign(claims)
