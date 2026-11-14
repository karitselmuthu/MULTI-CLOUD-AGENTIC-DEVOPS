"""Fail-closed settings for a private AWS sandbox deployment."""

import hmac
import os

from fastapi import HTTPException, Request
from temporalio.client import Client


def aws_sandbox_enabled() -> bool:
    return os.getenv("AWS_SANDBOX_MODE") == "1"


def validate_runtime() -> None:
    if os.getenv("AWS_SANDBOX_MODE", "0") not in {"0", "1"}:
        raise RuntimeError("AWS_SANDBOX_MODE must be 0 or 1")
    if not aws_sandbox_enabled():
        return
    required = (
        "DATABASE_URL", "TEMPORAL_ADDRESS", "TEMPORAL_NAMESPACE",
        "TEMPORAL_API_KEY", "LOCAL_DASHBOARD_TOKEN",
        "LOCAL_DASHBOARD_REQUESTER", "AGENT_SIGNING_KEY",
    )
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise RuntimeError("AWS sandbox configuration is incomplete: " + ", ".join(missing))
    if os.getenv("LOCAL_MOCK_APPROVAL_ENABLED") == "1":
        raise RuntimeError("local mock approval must be disabled in AWS sandbox mode")
    if not os.environ["TEMPORAL_ADDRESS"].endswith(":7233"):
        raise RuntimeError("Temporal Cloud address must use port 7233")


def require_sandbox_token(request: Request) -> None:
    if not aws_sandbox_enabled() or request.url.path == "/health":
        return
    expected = os.environ["LOCAL_DASHBOARD_TOKEN"]
    supplied = request.headers.get("authorization", "")
    if not hmac.compare_digest(supplied, f"Bearer {expected}"):
        raise HTTPException(status_code=403, detail="sandbox access denied")


async def connect_temporal() -> Client:
    address = os.environ["TEMPORAL_ADDRESS"]
    if aws_sandbox_enabled():
        return await Client.connect(
            address, namespace=os.environ["TEMPORAL_NAMESPACE"],
            api_key=os.environ["TEMPORAL_API_KEY"], tls=True,
        )
    return await Client.connect(address)
