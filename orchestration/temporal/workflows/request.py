"""Durable mock orchestration with digest-bound approval.

Sources: https://docs.temporal.io/develop/python/workflows/basics
         https://docs.temporal.io/develop/python/workflows/message-passing
         https://docs.temporal.io/encyclopedia/retry-policies
"""

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from orchestration.state.contracts import ApprovalCheck, MockPlan, WorkflowInput
    from orchestration.state.delivery import DeliveryReport
    from orchestration.temporal.activities.delivery import deliver_mock_plan
    from orchestration.temporal.activities.mock import execute_mock_plan, prepare_mock_plan, verify_mock_approval


@workflow.defn
class RequestWorkflow:
    def __init__(self) -> None:
        self.status = "received"
        self.plan: MockPlan | None = None
        self.report: DeliveryReport | None = None
        self.approval_tokens: list[str] = []

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
        deadline = workflow.now() + timedelta(hours=24)
        while True:
            remaining = deadline - workflow.now()
            if remaining <= timedelta():
                self.status = "approval_expired"
                return self.status
            try:
                await workflow.wait_condition(
                    lambda: bool(self.approval_tokens),
                    timeout=remaining,
                )
            except TimeoutError:
                self.status = "approval_expired"
                return self.status
            approval = ApprovalCheck(self.plan, value.request_json, self.approval_tokens.pop(0))
            if await workflow.execute_activity(
                verify_mock_approval, approval,
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=RetryPolicy(maximum_attempts=3),
            ):
                break
        self.status = "executing"
        result = await workflow.execute_activity(
            execute_mock_plan,
            approval,
            start_to_close_timeout=timedelta(seconds=30),
            schedule_to_close_timeout=timedelta(minutes=2),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )
        self.status = "delivering"
        self.report = await workflow.execute_activity(
            deliver_mock_plan,
            approval,
            start_to_close_timeout=timedelta(seconds=30),
            schedule_to_close_timeout=timedelta(minutes=2),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )
        self.status = "completed"
        return result

    @workflow.signal
    def approve(self, signed_approval: str) -> None:
        self.approval_tokens.append(signed_approval)

    @workflow.query
    def get_status(self) -> str:
        return self.status

    @workflow.query
    def get_plan(self) -> MockPlan | None:
        return self.plan

    @workflow.query
    def get_report(self) -> DeliveryReport | None:
        return self.report
