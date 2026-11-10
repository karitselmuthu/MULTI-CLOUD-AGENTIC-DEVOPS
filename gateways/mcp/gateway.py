"""Fail-closed local MCP tool gateway prototype.

OPA source: https://www.openpolicyagent.org/docs/cli
"""

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from security.identity.tokens import AgentClaims, ApprovalClaims, TokenVerifier


@dataclass(frozen=True)
class ToolContext:
    workflow_id: str
    plan_digest: str
    environment: str
    requester: str
    change_record: str | None


def approval_matches(approval: ApprovalClaims, context: ToolContext) -> bool:
    return (
        approval.workflow_id == context.workflow_id
        and approval.plan_digest == context.plan_digest
        and approval.environment == context.environment
        and approval.requester == context.requester
        and approval.change_record == context.change_record
        and approval.approver != context.requester
    )


class OpaPolicy:
    def __init__(self, binary: str | None = None, policy_path: Path | None = None):
        self.binary = binary or os.getenv("OPA_BIN", "opa")
        self.policy_path = policy_path or Path(__file__).parents[2] / "security/opa/tools.rego"

    def allows(self, policy_input: dict) -> bool:
        try:
            result = subprocess.run(
                [self.binary, "eval", "--stdin-input", "--data", str(self.policy_path),
                 "--format", "raw", "data.devops.tools.allow"],
                input=json.dumps(policy_input), text=True, capture_output=True,
                check=False, timeout=3,
            )
        except (OSError, subprocess.TimeoutExpired):
            return False
        return result.returncode == 0 and result.stdout.strip() == "true"


class MCPGateway:
    def __init__(self, verifier: TokenVerifier, policy: OpaPolicy):
        self.verifier = verifier
        self.policy = policy

    def call(self, agent_token: str, tool: str, context: ToolContext, approval_token: str | None = None) -> dict:
        agent = self.verifier.verify(agent_token, AgentClaims)
        if agent.workflow_id != context.workflow_id:
            raise PermissionError("agent token is for another workflow")
        approval_valid = False
        if approval_token is not None:
            try:
                approval = self.verifier.verify(approval_token, ApprovalClaims)
                approval_valid = approval_matches(approval, context)
            except PermissionError:
                approval_valid = False
        policy_input = {
            "agent": agent.model_dump(mode="json"),
            "workflow_id": context.workflow_id,
            "tool": tool,
            "environment": context.environment,
            "approval_valid": approval_valid,
        }
        if not self.policy.allows(policy_input):
            raise PermissionError("tool invocation denied")
        if tool == "catalog.read":
            return {"modules": ["sandbox-api"]}
        if tool == "mock.execute":
            return {"status": "simulated", "workflow_id": context.workflow_id, "plan_digest": context.plan_digest}
        raise PermissionError("unknown tool")
