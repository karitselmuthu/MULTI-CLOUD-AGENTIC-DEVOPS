"""Serializable contracts shared by Temporal workers and clients."""

from dataclasses import dataclass


@dataclass
class WorkflowInput:
    workflow_id: str
    request_json: str


@dataclass
class MockPlan:
    workflow_id: str
    cloud: str
    environment: str
    application: str
    digest: str


@dataclass
class ApprovalCheck:
    plan: MockPlan
    request_json: str
    approval_token: str
