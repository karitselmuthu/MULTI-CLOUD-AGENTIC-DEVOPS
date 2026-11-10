"""Approved, local-only delivery path. No external writes."""

from apps.api.contracts import RequestCreate
from temporalio import activity
from deployments.gitops.mock import MockGitOps
from integrations.github.mock import MockRepositoryAdapter
from orchestration.state.contracts import ApprovalCheck
from orchestration.state.delivery import DeliveryReport
from security.supply_chain.scanning import blocking, mock_scan


def simulate_delivery(value: ApprovalCheck, *, content: str | None = None, healthy: bool = True) -> DeliveryReport:
    request = RequestCreate.model_validate_json(value.request_json)
    content = content or (
        "from fastapi import FastAPI\n"
        "app = FastAPI()\n"
        "@app.get('/health')\n"
        "def health():\n"
        "    return {'status': 'ok'}\n"
    )
    findings = mock_scan(content)
    if blocking(findings):
        raise ValueError("blocking security finding in generated code")
    pr = MockRepositoryAdapter().propose(
        request.application.repository, value.plan.workflow_id, content
    )
    # The mock CI gate is deterministic: the generated source must compile.
    compile(content, "generated_service.py", "exec")
    deployment = MockGitOps().reconcile(pr.commit_digest, healthy=healthy)
    return DeliveryReport(
        workflow_id=value.plan.workflow_id,
        plan_digest=value.plan.digest,
        branch=pr.branch,
        pull_request=pr.url,
        commit_digest=pr.commit_digest,
        ci_passed=True,
        security_passed=True,
        deployment_status=deployment.status,
        deployment_revision=deployment.revision,
    )


@activity.defn
async def deliver_mock_plan(value: ApprovalCheck) -> DeliveryReport:
    return simulate_delivery(value)
