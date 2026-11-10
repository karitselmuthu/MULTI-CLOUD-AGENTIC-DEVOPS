"""Control plane intake API. No cloud execution occurs in this slice.

Sources: https://fastapi.tiangolo.com/tutorial/body/
         https://fastapi.tiangolo.com/tutorial/response-status-code/
"""

import hashlib
from datetime import timezone
from uuid import UUID, uuid4

from fastapi import FastAPI, Header, HTTPException
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from .contracts import HealthResponse, RequestCreate, WorkflowResponse
from .database import AuditEvent, WorkflowRecord, make_session_factory, utc_now


def create_app(session_factory=None) -> FastAPI:
    sessions = session_factory or make_session_factory()
    app = FastAPI(title="Enterprise Multi-Cloud Agentic DevOps", version="0.1.0")

    def response_for(row: WorkflowRecord) -> WorkflowResponse:
        created_at = row.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        return WorkflowResponse(
            id=UUID(row.id), status=row.status, cloud=row.cloud,
            environment=row.environment, created_at=created_at,
            request_digest=row.request_digest,
        )

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        try:
            with sessions() as session:
                session.execute(text("SELECT 1"))
        except Exception as exc:
            raise HTTPException(status_code=503, detail="database unavailable") from exc
        return HealthResponse(status="ok")

    @app.post("/requests", response_model=WorkflowResponse, status_code=202)
    def submit_request(
        request: RequestCreate,
        idempotency_key: str = Header(min_length=1, max_length=128),
    ) -> WorkflowResponse:
        payload = request.model_dump_json()
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
    def get_workflow(workflow_id: UUID) -> WorkflowResponse:
        with sessions() as session:
            row = session.get(WorkflowRecord, str(workflow_id))
            if row is None:
                raise HTTPException(status_code=404, detail="workflow not found")
            return response_for(row)

    return app


app = create_app()
