"""Local TACOS run, lock, budget, and drift simulation.

HCP run states: https://developer.hashicorp.com/terraform/cloud-docs/api-docs/run
HCP workspace locking: https://developer.hashicorp.com/terraform/cloud-docs/workspaces/settings
"""

from dataclasses import dataclass
import re
from threading import RLock

from gateways.mcp.gateway import ToolContext, approval_matches
from security.identity.tokens import ApprovalClaims, TokenVerifier, WorkloadClaims


@dataclass(frozen=True)
class Workspace:
    tenant: str
    cloud: str
    environment: str
    budget_limit: int


@dataclass(frozen=True)
class TacosRun:
    workspace: Workspace
    workflow_id: str
    plan_digest: str
    requester: str
    change_record: str | None
    estimated_cost: int
    status: str


class MockTacos:
    def __init__(self, verifier: TokenVerifier):
        self._verifier = verifier
        self._lock = RLock()
        self._runs: dict[str, TacosRun] = {}
        self._workspace_locks: set[Workspace] = set()
        self._spent: dict[Workspace, int] = {}
        self._drift: set[Workspace] = set()

    def plan(self, run: TacosRun) -> TacosRun:
        if run.workspace.environment != "sandbox" or run.status != "planned":
            raise PermissionError("only sandbox plans are supported")
        if run.workspace.cloud not in {"aws", "azure"} or not run.workspace.tenant:
            raise ValueError("unsupported cloud or tenant")
        if run.estimated_cost < 0 or run.workspace.budget_limit <= 0 or not re.fullmatch(r"[0-9a-f]{64}", run.plan_digest):
            raise ValueError("invalid plan estimate or digest")
        with self._lock:
            if run.workflow_id in self._runs:
                existing = self._runs[run.workflow_id]
                if existing != run:
                    raise ValueError("workflow id reused with a different plan")
                return existing
            self._runs[run.workflow_id] = run
            return run

    def apply(self, workflow_id: str, approval_token: str, workload_token: str) -> TacosRun:
        approval = self._verifier.verify(approval_token, ApprovalClaims)
        workload = self._verifier.verify(workload_token, WorkloadClaims)
        with self._lock:
            run = self._runs[workflow_id]
            if workload.tenant != run.workspace.tenant or workload.workflow_id != workflow_id or workload.plan_digest != run.plan_digest:
                raise PermissionError("workload scope does not match run")
            context = ToolContext(workflow_id, run.plan_digest, run.workspace.environment, run.requester, run.change_record)
            if not approval_matches(approval, context):
                raise PermissionError("approval does not match run")
            if run.status == "applied":
                return run
            if run.workspace in self._drift:
                raise PermissionError("workspace drift requires review")
            if run.workspace in self._workspace_locks:
                raise RuntimeError("workspace locked")
            if self._spent.get(run.workspace, 0) + run.estimated_cost > run.workspace.budget_limit:
                raise PermissionError("tenant budget exceeded")
            self._workspace_locks.add(run.workspace)
            try:
                applied = TacosRun(**{**run.__dict__, "status": "applied"})
                self._runs[workflow_id] = applied
                self._spent[run.workspace] = self._spent.get(run.workspace, 0) + run.estimated_cost
                return applied
            finally:
                self._workspace_locks.remove(run.workspace)

    def record_drift(self, workspace: Workspace) -> None:
        with self._lock:
            self._drift.add(workspace)

    def has_drift(self, workspace: Workspace) -> bool:
        with self._lock:
            return workspace in self._drift
