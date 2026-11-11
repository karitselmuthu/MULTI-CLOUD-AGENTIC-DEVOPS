"""Issue a local mock approval after an independent reviewer inspects the plan.

Source: https://www.python-httpx.org/quickstart/
"""

import argparse
import os
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit
from uuid import UUID

import httpx

from apps.api.contracts import RequestCreate, WorkflowResponse
from security.identity.tokens import ApprovalClaims, TokenVerifier


def validate_local_url(url: str) -> str:
    parsed = urlsplit(url)
    if (parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
            or parsed.username or parsed.password or parsed.path not in {"", "/"}
            or parsed.query or parsed.fragment or parsed.port is None):
        raise ValueError("mock approval API must be a loopback HTTP URL with a port")
    return url.rstrip("/")


def load_detail(client: httpx.Client, workflow_id: str, dashboard_token: str) -> dict:
    normalized_id = str(UUID(workflow_id))
    response = client.get(
        f"/dashboard/workflows/{normalized_id}",
        headers={"Authorization": f"Bearer {dashboard_token}"},
        timeout=10.0,
    )
    response.raise_for_status()
    return response.json()


def issue_from_detail(detail: dict, approver: str, signing_key: str) -> str:
    workflow = WorkflowResponse.model_validate(detail["workflow"])
    request = RequestCreate.model_validate(detail["request"])
    plan = detail.get("plan")
    if workflow.status != "awaiting_approval" or not plan:
        raise ValueError("workflow is not awaiting approval")
    if workflow.plan_digest is None or workflow.plan_digest != plan.get("digest"):
        raise ValueError("plan digest does not match workflow")
    if workflow.cloud != request.cloud or workflow.environment != request.environment:
        raise ValueError("request and workflow cloud or environment differ")
    if not approver.strip() or approver.strip() == request.requester:
        raise ValueError("approval requires a separate approver")
    claims = ApprovalClaims(
        workflow_id=str(workflow.id), plan_digest=workflow.plan_digest,
        environment=request.environment.value, requester=request.requester,
        change_record=request.approval.change_record, approver=approver.strip(),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )
    return TokenVerifier(signing_key.encode()).sign(claims)


def main() -> None:
    parser = argparse.ArgumentParser(description="Issue a local, plan-bound mock approval token")
    parser.add_argument("--workflow-id", required=True)
    parser.add_argument("--approver", default="local-mock-reviewer")
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    if os.getenv("LOCAL_MOCK_APPROVAL_ENABLED") != "1":
        parser.error("local mock approval is disabled")
    dashboard_token = os.getenv("LOCAL_DASHBOARD_TOKEN", "")
    signing_key = os.getenv("AGENT_SIGNING_KEY", "")
    if not dashboard_token or not signing_key:
        parser.error("source the shared .env before issuing a mock approval")
    try:
        api_url = validate_local_url(args.api_url)
        with httpx.Client(base_url=api_url) as client:
            detail = load_detail(client, args.workflow_id, dashboard_token)
        print(issue_from_detail(detail, args.approver, signing_key))
    except (ValueError, httpx.HTTPError, KeyError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
