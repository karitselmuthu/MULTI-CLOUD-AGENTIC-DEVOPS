"""Workflow evidence evaluation, independent of model and deployment quality."""


def workflow_reliability_passes(status: str, event_types: list[str]) -> bool:
    required = {"request.received", "workflow.dispatched", "approval.signaled"}
    return status == "completed" and required.issubset(event_types) and event_types.count("request.received") == 1
