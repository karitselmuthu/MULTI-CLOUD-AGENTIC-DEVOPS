"""Serializable evidence for the local delivery simulation."""

from dataclasses import dataclass


@dataclass
class DeliveryReport:
    workflow_id: str
    plan_digest: str
    branch: str
    pull_request: str
    commit_digest: str
    image_ref: str
    ci_passed: bool
    security_passed: bool
    supply_chain_passed: bool
    deployment_status: str
    deployment_revision: str

