"""Durable mock orchestration with digest-bound approval.

Sources: https://docs.temporal.io/develop/python/workflows/basics
         https://docs.temporal.io/develop/python/workflows/message-passing
         https://docs.temporal.io/encyclopedia/retry-policies
"""

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from orchestration.state.contracts import MockPlan, WorkflowInput
    from orchestration.temporal.activities.mock import execute_mock_plan, prepare_mock_plan


@workflow.defn
class RequestWorkflow:
    def __init__(self) -> None:
        self.status = "received"
        self.plan: MockPlan | None = None
        self.approval_digest: str | None = None

    @workflow.run
    async def run(self, value: WorkflowInput) -> str:
        self.status = "planning"
        self.plan = await workflow.execute_activity(
            prepare_mock_plan,
            value,
            start_to_close_timeout=timedelta(seconds=30),
            schedule_to_close_timeout=timedelta(minutes=2),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )
        self.status = "awaiting_approval"
        try:
            await workflow.wait_condition(
                lambda: self.approval_digest == self.plan.digest,
                timeout=timedelta(hours=24),
            )
        except TimeoutError:
            self.status = "approval_expired"
            return self.status
        self.status = "executing"
        result = await workflow.execute_activity(
            execute_mock_plan,
            self.plan,
            start_to_close_timeout=timedelta(seconds=30),
            schedule_to_close_timeout=timedelta(minutes=2),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )
        self.status = "completed"
        return result

    @workflow.signal
    def approve(self, digest: str) -> None:
        self.approval_digest = digest

    @workflow.query
    def get_status(self) -> str:
        return self.status

    @workflow.query
    def get_plan(self) -> MockPlan | None:
        return self.plan
