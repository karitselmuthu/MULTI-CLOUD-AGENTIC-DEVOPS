"""Local ITSM approval signal and CAB evidence record."""

import hashlib
from dataclasses import dataclass

from gateways.mcp.gateway import ToolContext, approval_matches
from security.identity.tokens import ApprovalClaims, TokenVerifier


@dataclass(frozen=True)
class ChangeRecord:
    change_id: str
    tenant: str
    workflow_id: str
    plan_digest: str
    requester: str
    environment: str
    status: str
    cab_evidence_digest: str | None = None


class MockChangeService:
    def __init__(self, verifier: TokenVerifier):
        self._verifier = verifier
        self._records: dict[str, ChangeRecord] = {}

    def create(self, *, tenant: str, workflow_id: str, plan_digest: str,
               requester: str, environment: str) -> ChangeRecord:
        change_id = "CHG-" + hashlib.sha256(f"{tenant}:{workflow_id}".encode()).hexdigest()[:12]
        value = ChangeRecord(change_id, tenant, workflow_id, plan_digest,
                             requester, environment, "awaiting_approval")
        existing = self._records.setdefault(change_id, value)
        if (existing.tenant, existing.workflow_id, existing.plan_digest,
            existing.requester, existing.environment) != (
            tenant, workflow_id, plan_digest, requester, environment
        ):
            raise ValueError("change id reused with different plan")
        return existing

    def approve(self, change_id: str, approval_token: str, cab_evidence: bytes) -> ChangeRecord:
        if not cab_evidence:
            raise ValueError("CAB evidence is required")
        record = self._records[change_id]
        approval = self._verifier.verify(approval_token, ApprovalClaims)
        context = ToolContext(record.workflow_id, record.plan_digest,
                              record.environment, record.requester, change_id)
        if not approval_matches(approval, context):
            raise PermissionError("approval does not match change")
        evidence_digest = hashlib.sha256(cab_evidence).hexdigest()
        updated = ChangeRecord(**{**record.__dict__, "status": "approved",
                                  "cab_evidence_digest": evidence_digest})
        if record.status == "approved" and record != updated:
            raise ValueError("CAB evidence changed after approval")
        self._records[change_id] = updated
        return updated
