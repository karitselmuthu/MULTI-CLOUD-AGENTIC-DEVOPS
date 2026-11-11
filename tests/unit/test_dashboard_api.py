from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from apps.api.database import Base
from apps.api.main import create_app
from tests.unit.test_api import request_body


def test_dashboard_requires_token_and_limits_requester(monkeypatch):
    monkeypatch.setenv("LOCAL_DASHBOARD_TOKEN", "local-dashboard-secret")
    monkeypatch.setenv("LOCAL_DASHBOARD_REQUESTER", "engineer@example.com")
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    sessions = sessionmaker(engine, expire_on_commit=False)
    with TestClient(create_app(sessions)) as client:
        first = client.post("/requests", json=request_body(), headers={"Idempotency-Key": "one"}).json()
        other = request_body()
        other["requester"] = "other@example.com"
        second = client.post("/requests", json=other, headers={"Idempotency-Key": "two"}).json()
        auth = {"Authorization": "Bearer local-dashboard-secret"}
        assert client.get("/dashboard/workflows").status_code == 403
        rows = client.get("/dashboard/workflows", headers=auth).json()
        assert [row["id"] for row in rows] == [first["id"]]
        assert client.get(f"/dashboard/workflows/{second['id']}", headers=auth).status_code == 404
        detail = client.get(f"/dashboard/workflows/{first['id']}", headers=auth).json()
        assert detail["request"]["application"]["name"] == "sample-api"
        assert detail["events"][0]["type"] == "request.received"
        assert client.post("/dashboard/requests", json=other,
                           headers={**auth, "Idempotency-Key": "three"}).status_code == 403
    engine.dispose()
