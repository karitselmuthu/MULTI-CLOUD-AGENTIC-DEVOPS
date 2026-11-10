"""Start accepted requests from the database-backed dispatch queue.

Source: https://python.temporal.io/temporalio.client.Client.html
"""

from temporalio.common import WorkflowIDReusePolicy
from temporalio.exceptions import WorkflowAlreadyStartedError
from sqlalchemy import select

from apps.api.database import AuditEvent, WorkflowRecord, utc_now
from orchestration.state.contracts import WorkflowInput
from orchestration.temporal.workflows.request import RequestWorkflow

TASK_QUEUE = "devops-requests"


async def dispatch_once(client, sessions) -> int:
    dispatched = 0
    with sessions() as session:
        pending_ids = session.scalars(
            select(WorkflowRecord.id).where(WorkflowRecord.status == "received").limit(100)
        ).all()
    for workflow_id in pending_ids:
        with sessions() as session:
            row = session.get(WorkflowRecord, workflow_id)
            if row is None or row.status != "received":
                continue
            request_json = row.request_json
        try:
            await client.start_workflow(
                RequestWorkflow.run,
                WorkflowInput(workflow_id=workflow_id, request_json=request_json),
                id=workflow_id,
                task_queue=TASK_QUEUE,
                id_reuse_policy=WorkflowIDReusePolicy.REJECT_DUPLICATE,
            )
        except WorkflowAlreadyStartedError:
            # The previous dispatcher may have crashed after Temporal accepted the start.
            pass
        with sessions() as session:
            row = session.get(WorkflowRecord, workflow_id)
            if row is None or row.status != "received":
                continue
            row.status = "queued"
            session.add(AuditEvent(workflow=row, event_type="workflow.dispatched", created_at=utc_now()))
            session.commit()
            dispatched += 1
    return dispatched
