"""Run-scoped agent and exact-context approval tokens for the local prototype.

Source: https://docs.python.org/3/library/hmac.html
"""

import base64
import binascii
import hashlib
import hmac
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class AgentClaims(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["agent"] = "agent"
    role: Literal["planning", "devops"]
    workflow_id: str = Field(min_length=1)
    expires_at: datetime


class ApprovalClaims(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["approval"] = "approval"
    workflow_id: str = Field(min_length=1)
    plan_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    environment: str = Field(min_length=1)
    requester: str = Field(min_length=1)
    change_record: str | None = None
    approver: str = Field(min_length=1)
    expires_at: datetime


class WorkloadClaims(BaseModel):
    """Tenant and action scoped mock workload identity; not a cloud credential."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["workload"] = "workload"
    tenant: str = Field(min_length=1)
    role: Literal["tacos-executor"]
    workflow_id: str = Field(min_length=1)
    plan_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    expires_at: datetime


class TokenVerifier:
    def __init__(self, secret: bytes):
        if len(secret) < 32:
            raise ValueError("signing secret must be at least 32 bytes")
        self._secret = secret
        self._revoked: set[str] = set()

    def revoke(self, token: str) -> None:
        """Revoke within this verifier instance; not a distributed revocation list."""
        self._revoked.add(hashlib.sha256(token.encode()).hexdigest())

    def sign(self, claims: AgentClaims | ApprovalClaims | WorkloadClaims) -> str:
        payload = claims.model_dump_json().encode()
        signature = hmac.new(self._secret, payload, hashlib.sha256).digest()
        return f"{_encode(payload)}.{_encode(signature)}"

    def verify(self, token: str, claims_type: type[AgentClaims] | type[ApprovalClaims] | type[WorkloadClaims]):
        try:
            if hashlib.sha256(token.encode()).hexdigest() in self._revoked:
                raise ValueError("token revoked")
            payload_part, signature_part = token.split(".")
            payload = _decode(payload_part)
            signature = _decode(signature_part)
            expected = hmac.new(self._secret, payload, hashlib.sha256).digest()
            if not hmac.compare_digest(signature, expected):
                raise ValueError("invalid signature")
            claims = claims_type.model_validate_json(payload)
            if claims.expires_at.tzinfo is None or claims.expires_at <= datetime.now(timezone.utc):
                raise ValueError("token expired or has no timezone")
            return claims
        except (ValueError, ValidationError, TypeError, binascii.Error, UnicodeError) as exc:
            raise PermissionError("invalid or expired token") from exc


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
