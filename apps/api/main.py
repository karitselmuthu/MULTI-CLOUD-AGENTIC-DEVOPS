"""Control plane intake API. No cloud execution occurs in this slice.

Sources: https://fastapi.tiangolo.com/tutorial/body/
         https://fastapi.tiangolo.com/tutorial/response-status-code/
"""

import hashlib
import hmac
import os
import asyncio
from datetime import timezone
from uuid import UUID, uuid4

from fastapi import FastAPI, Header, HTTPException
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from temporalio.client import Client

from .contracts import ApprovalSubmission, HealthResponse, RequestCreate, WorkflowResponse
from .database import AuditEvent, WorkflowRecord, make_session_factory, utc_now
from gateways.mcp.gateway import ToolContext, approval_matches
from orchestration.state.delivery import DeliveryReport
from orchestration.temporal.workflows.request import RequestWorkflow
from observability.otel.correlation import workflow_span
from security.identity.tokens import ApprovalClaims, TokenVerifier


def create_app(session_factory=None, temporal_client=None) -> FastAPI:
    sessions = session_factory or make_session_factory()
    app = FastAPI(title="Enterprise Multi-Cloud Agentic DevOps", version="0.1.0")

    def dashboard_requester(token: str | None) -> str:
        expected = os.environ.get("LOCAL_DASHBOARD_TOKEN", "")
        requester = os.environ.get("LOCAL_DASHBOARD_REQUESTER", "")
        if (not expected or not requester or not token or
                not hmac.compare_digest(token, f"Bearer {expected}")):
            raise HTTPException(status_code=403, detail="dashboard access denied")
        return requester

    async def get_temporal():
        if temporal_client is not None:
            return temporal_client
        address = os.environ.get("TEMPORAL_ADDRESS")
        if not address:
            raise HTTPException(status_code=503, detail="Temporal is not configured")
        try:
            return await Client.connect(address)
        except Exception as exc:
            raise HTTPException(status_code=503, detail="Temporal unavailable") from exc

    def response_for(row: WorkflowRecord, status: str | None = None, plan_digest: str | None = None) -> WorkflowResponse:
        created_at = row.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        return WorkflowResponse(
            id=UUID(row.id), status=status or row.status, cloud=row.cloud,
            environment=row.environment, created_at=created_at,
            request_digest=row.request_digest, plan_digest=plan_digest,
        )

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        try:
            with sessions() as session:
                session.execute(text("SELECT 1"))
        except Exception as exc:
            raise HTTPException(status_code=503, detail="database unavailable") from exc
        return HealthResponse(status="ok")

    @app.get("/dashboard/workflows")
    async def dashboard_workflows(authorization: str | None = Header(default=None)) -> list[WorkflowResponse]:
        requester = dashboard_requester(authorization)
        with sessions() as session:
            rows = session.scalars(select(WorkflowRecord).order_by(WorkflowRecord.created_at.desc())).all()
            visible = [row for row in rows
                       if RequestCreate.model_validate_json(row.request_json).requester == requester][:200]
            result = [response_for(row) for row in visible]
        queued = [(index, row) for index, row in enumerate(visible) if row.status == "queued"]
        if queued and (temporal_client is not None or os.environ.get("TEMPORAL_ADDRESS")):
            client = await get_temporal()
            semaphore = asyncio.Semaphore(10)

            async def current(index: int, row: WorkflowRecord):
                async with semaphore:
                    handle = client.get_workflow_handle(row.id)
                    status = await handle.query(RequestWorkflow.get_status)
                    plan = await handle.query(RequestWorkflow.get_plan)
                    result[index] = response_for(row, status=status, plan_digest=plan.digest if plan else None)

            try:
                await asyncio.gather(*(current(index, row) for index, row in queued))
            except Exception as exc:
                raise HTTPException(status_code=503, detail="workflow state unavailable") from exc
        return result

    @app.get("/dashboard/workflows/{workflow_id}")
    async def dashboard_workflow(workflow_id: UUID, authorization: str | None = Header(default=None)) -> dict:
        requester = dashboard_requester(authorization)
        with sessions() as session:
            row = session.get(WorkflowRecord, str(workflow_id))
            if row is None:
                raise HTTPException(status_code=404, detail="workflow not found")
            request = RequestCreate.model_validate_json(row.request_json)
            if request.requester != requester:
                raise HTTPException(status_code=404, detail="workflow not found")
            audit_rows = session.scalars(select(AuditEvent).where(
                AuditEvent.workflow_id == str(workflow_id)).order_by(AuditEvent.id)).all()
            events = [{"type": event.event_type, "at": event.created_at.isoformat()}
                      for event in audit_rows]
            summary = response_for(row).model_dump(mode="json")
            queued = row.status == "queued"
        plan = report = None
        if queued:
            with workflow_span(str(workflow_id), "dashboard.workflow_detail"):
                client = await get_temporal()
                handle = client.get_workflow_handle(str(workflow_id))
                try:
                    status = await handle.query(RequestWorkflow.get_status)
                    plan = await handle.query(RequestWorkflow.get_plan)
                    report = await handle.query(RequestWorkflow.get_report)
                except Exception as exc:
                    raise HTTPException(status_code=503, detail="workflow state unavailable") from exc
            summary["status"] = status
            summary["plan_digest"] = plan.digest if plan else None
        return {"workflow": summary, "request": request.model_dump(mode="json"),
                "events": events, "plan": vars(plan) if plan else None,
                "report": vars(report) if report else None}

    @app.post("/dashboard/requests", response_model=WorkflowResponse, status_code=202)
    def dashboard_submit(request: RequestCreate, idempotency_key: str = Header(min_length=1, max_length=128),
                         authorization: str | None = Header(default=None)) -> WorkflowResponse:
        requester = dashboard_requester(authorization)
        if request.requester != requester:
            raise HTTPException(status_code=403, detail="requester mismatch")
        return submit_request(request, idempotency_key)

    @app.post("/requests", response_model=WorkflowResponse, status_code=202)
    def submit_request(
        request: RequestCreate,
        idempotency_key: str = Header(min_length=1, max_length=128),
    ) -> WorkflowResponse:
        # Preserve the canonical bytes of pre-portal requests when new fields are absent.
        optional_exclusions = {name for name in ("cost_center", "description") if getattr(request, name) is None}
        payload = request.model_dump_json(exclude=optional_exclusions)
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        with sessions() as session:
            existing = session.scalar(select(WorkflowRecord).where(WorkflowRecord.idempotency_key == idempotency_key))
            if existing:
                if existing.request_digest != digest:
                    raise HTTPException(status_code=409, detail="idempotency key reused with different request")
                return response_for(existing)

            now = utc_now()
            row = WorkflowRecord(
                id=str(uuid4()), idempotency_key=idempotency_key,
                request_digest=digest, request_json=payload,
                cloud=request.cloud.value, environment=request.environment.value,
                status="received", created_at=now,
            )
            session.add(row)
            session.add(AuditEvent(workflow=row, event_type="request.received", created_at=now))
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                winner = session.scalar(select(WorkflowRecord).where(WorkflowRecord.idempotency_key == idempotency_key))
                if winner is None:
                    raise
                if winner.request_digest != digest:
                    raise HTTPException(status_code=409, detail="idempotency key conflict")
                return response_for(winner)
            return response_for(row)

    @app.get("/workflows/{workflow_id}", response_model=WorkflowResponse)
    async def get_workflow(workflow_id: UUID) -> WorkflowResponse:
        with sessions() as session:
            row = session.get(WorkflowRecord, str(workflow_id))
            if row is None:
                raise HTTPException(status_code=404, detail="workflow not found")
            if row.status != "queued" or (temporal_client is None and not os.environ.get("TEMPORAL_ADDRESS")):
                return response_for(row)
            response_row = row
        client = await get_temporal()
        handle = client.get_workflow_handle(str(workflow_id))
        try:
            status = await handle.query(RequestWorkflow.get_status)
            plan = await handle.query(RequestWorkflow.get_plan)
        except Exception as exc:
            raise HTTPException(status_code=503, detail="workflow state unavailable") from exc
        return response_for(response_row, status=status, plan_digest=plan.digest if plan else None)

    @app.post("/workflows/{workflow_id}/approve", status_code=202)
    async def approve_workflow(workflow_id: UUID, submission: ApprovalSubmission) -> dict[str, str]:
        with sessions() as session:
            row = session.get(WorkflowRecord, str(workflow_id))
            if row is None:
                raise HTTPException(status_code=404, detail="workflow not found")
            request = RequestCreate.model_validate_json(row.request_json)
        client = await get_temporal()
        handle = client.get_workflow_handle(str(workflow_id))
        try:
            status = await handle.query(RequestWorkflow.get_status)
            plan = await handle.query(RequestWorkflow.get_plan)
        except Exception as exc:
            raise HTTPException(status_code=503, detail="workflow state unavailable") from exc
        if status != "awaiting_approval" or plan is None:
            raise HTTPException(status_code=409, detail="workflow is not awaiting approval")
        try:
            verifier = TokenVerifier(os.environ.get("AGENT_SIGNING_KEY", "").encode())
            approval = verifier.verify(submission.signed_approval, ApprovalClaims)
        except (ValueError, PermissionError) as exc:
            raise HTTPException(status_code=403, detail="invalid approval") from exc
        context = ToolContext(
            workflow_id=str(workflow_id), plan_digest=plan.digest,
            environment=request.environment.value, requester=request.requester,
            change_record=request.approval.change_record,
        )
        if not approval_matches(approval, context):
            raise HTTPException(status_code=403, detail="approval does not match plan")
        await handle.signal(RequestWorkflow.approve, submission.signed_approval)
        with sessions() as session, session.begin():
            session.add(AuditEvent(workflow_id=str(workflow_id), event_type="approval.signaled", created_at=utc_now()))
        return {"status": "approval_signaled"}

    @app.get("/workflows/{workflow_id}/report", response_model=DeliveryReport)
    async def get_report(workflow_id: UUID) -> DeliveryReport:
        with sessions() as session:
            row = session.get(WorkflowRecord, str(workflow_id))
            if row is None:
                raise HTTPException(status_code=404, detail="workflow not found")
            if row.status != "queued":
                raise HTTPException(status_code=409, detail="workflow has not started")
        client = await get_temporal()
        handle = client.get_workflow_handle(str(workflow_id))
        try:
            report = await handle.query(RequestWorkflow.get_report)
        except Exception as exc:
            raise HTTPException(status_code=503, detail="workflow report unavailable") from exc
        if report is None:
            raise HTTPException(status_code=409, detail="delivery has not completed")
        return report

    return app


app = create_app()
