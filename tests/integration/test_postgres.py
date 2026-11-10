"""Runs only when TEST_DATABASE_URL points at a disposable PostgreSQL database."""

import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from apps.api.database import AuditEvent, Base, WorkflowRecord
from apps.api.main import create_app


def test_postgres_intake_survives_app_restart():
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL is not set")
    if not url.startswith("postgresql+psycopg://"):
        pytest.fail("TEST_DATABASE_URL must be a PostgreSQL psycopg URL")
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    sessions = sessionmaker(engine, expire_on_commit=False)
    key = f"pg-{uuid4()}"
    body = {
        "cloud": "azure", "environment": "sandbox", "requester": "engineer@example.com",
        "application": {"name": "sample-api", "repository": "https://github.com/example/sample-api"},
        "infrastructure": {"region": "eastus", "module": "sandbox-api"},
        "approval": {"required": True},
    }
    with TestClient(create_app(sessions)) as first:
        response = first.post("/requests", json=body, headers={"Idempotency-Key": key})
        assert response.status_code == 202
        workflow_id = response.json()["id"]
    with TestClient(create_app(sessions)) as restarted:
        assert restarted.get(f"/workflows/{workflow_id}").json()["id"] == workflow_id
        replay = restarted.post("/requests", json=body, headers={"Idempotency-Key": key})
        assert replay.json()["id"] == workflow_id
    with sessions() as session:
        assert session.get(WorkflowRecord, workflow_id) is not None
        assert len(session.scalars(select(AuditEvent).where(AuditEvent.workflow_id == workflow_id)).all()) == 1
    engine.dispose()
