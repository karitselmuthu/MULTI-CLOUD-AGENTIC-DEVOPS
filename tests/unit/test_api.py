from hashlib import sha256
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from apps.api.database import AuditEvent, Base, WorkflowRecord
from apps.api.main import create_app


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sessions = sessionmaker(engine, expire_on_commit=False)
    with TestClient(create_app(sessions)) as test_client:
        yield test_client, sessions
    engine.dispose()


def request_body(cloud="aws"):
    return {
        "cloud": cloud,
        "environment": "sandbox",
        "requester": "engineer@example.com",
        "application": {"name": "sample-api", "repository": "https://github.com/example/sample-api"},
        "infrastructure": {"region": "us-east-1", "module": "sandbox-api"},
        "approval": {"required": True},
    }


@pytest.mark.parametrize("cloud", ["aws", "azure"])
def test_submit_and_read(client, cloud):
    http, sessions = client
    response = http.post("/requests", json=request_body(cloud), headers={"Idempotency-Key": cloud})
    assert response.status_code == 202
    workflow = response.json()
    assert UUID(workflow["id"])
    assert workflow["cloud"] == cloud
    assert workflow["status"] == "received"
    assert http.get(f"/workflows/{workflow['id']}").json() == workflow
    with sessions() as session:
        events = session.scalars(select(AuditEvent)).all()
        assert len(events) == 1
        assert events[0].event_type == "request.received"


def test_invalid_input_and_missing_idempotency_key(client):
    http, _ = client
    bad = request_body("gcp")
    assert http.post("/requests", json=bad, headers={"Idempotency-Key": "bad"}).status_code == 422
    assert http.post("/requests", json=request_body()).status_code == 422
    bad = request_body()
    bad["approval"] = {"required": False}
    assert http.post("/requests", json=bad, headers={"Idempotency-Key": "bad"}).status_code == 422


def test_plain_text_description_bounds_are_enforced(client):
    http, _ = client
    for description in ("<script>alert(1)</script>", "x" * 2001):
        payload = request_body()
        payload["cost_center"] = "CC-123"
        payload["description"] = description
        assert http.post("/requests", json=payload, headers={"Idempotency-Key": "description"}).status_code == 422
    payload["description"] = "Private network for sandbox API"
    assert http.post("/requests", json=payload, headers={"Idempotency-Key": "description"}).status_code == 202


def test_legacy_request_digest_stays_compatible(client):
    http, sessions = client
    response = http.post("/requests", json=request_body(), headers={"Idempotency-Key": "legacy"})
    assert response.status_code == 202
    legacy_json = ('{"cloud":"aws","environment":"sandbox","requester":"engineer@example.com",'
                   '"application":{"name":"sample-api","repository":"https://github.com/example/sample-api"},'
                   '"infrastructure":{"region":"us-east-1","module":"sandbox-api"},'
                   '"approval":{"required":true,"change_record":null}}')
    with sessions() as session:
        row = session.get(WorkflowRecord, response.json()["id"])
        assert row.request_json == legacy_json
        assert row.request_digest == sha256(legacy_json.encode()).hexdigest()


def test_duplicate_request_is_idempotent_and_conflict_is_rejected(client):
    http, sessions = client
    headers = {"Idempotency-Key": "same-key"}
    first = http.post("/requests", json=request_body(), headers=headers)
    second = http.post("/requests", json=request_body(), headers=headers)
    assert first.status_code == second.status_code == 202
    assert first.json()["id"] == second.json()["id"]
    changed = request_body()
    changed["environment"] = "prod"
    assert http.post("/requests", json=changed, headers=headers).status_code == 409
    with sessions() as session:
        assert len(session.scalars(select(AuditEvent)).all()) == 1


def test_health_and_unknown_workflow(client):
    http, _ = client
    assert http.get("/health").json() == {"status": "ok"}
    assert http.get("/workflows/00000000-0000-0000-0000-000000000000").status_code == 404


def test_record_survives_new_app_instance(tmp_path):
    db_path = tmp_path / "intake.db"
    engine = create_engine(f"sqlite+pysqlite:///{db_path}")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(engine, expire_on_commit=False)
    with TestClient(create_app(sessions)) as first_app:
        created = first_app.post(
            "/requests", json=request_body(), headers={"Idempotency-Key": "restart"}
        ).json()
    with TestClient(create_app(sessions)) as restarted_app:
        assert restarted_app.get(f"/workflows/{created['id']}").json() == created
    engine.dispose()
