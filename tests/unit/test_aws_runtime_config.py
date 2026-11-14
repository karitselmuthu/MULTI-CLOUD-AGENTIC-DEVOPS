import pytest
from fastapi import HTTPException
from starlette.requests import Request

from apps.api.runtime_config import require_sandbox_token, validate_runtime


def test_aws_mode_fails_closed_without_runtime_secrets(monkeypatch):
    monkeypatch.setenv("AWS_SANDBOX_MODE", "1")
    for key in (
        "DATABASE_URL", "TEMPORAL_ADDRESS", "TEMPORAL_NAMESPACE", "TEMPORAL_API_KEY",
        "LOCAL_DASHBOARD_TOKEN", "LOCAL_DASHBOARD_REQUESTER", "AGENT_SIGNING_KEY",
    ):
        monkeypatch.delenv(key, raising=False)
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        validate_runtime()


def test_unknown_aws_mode_fails_closed(monkeypatch):
    monkeypatch.setenv("AWS_SANDBOX_MODE", "production")
    with pytest.raises(RuntimeError, match="must be 0 or 1"):
        validate_runtime()


def test_aws_mode_rejects_local_mock_issuer(monkeypatch):
    monkeypatch.setenv("AWS_SANDBOX_MODE", "1")
    for key in (
        "DATABASE_URL", "TEMPORAL_ADDRESS", "TEMPORAL_NAMESPACE", "TEMPORAL_API_KEY",
        "LOCAL_DASHBOARD_TOKEN", "LOCAL_DASHBOARD_REQUESTER", "AGENT_SIGNING_KEY",
    ):
        monkeypatch.setenv(key, "configured")
    monkeypatch.setenv("TEMPORAL_ADDRESS", "example.tmprl.cloud:7233")
    monkeypatch.setenv("LOCAL_MOCK_APPROVAL_ENABLED", "1")
    with pytest.raises(RuntimeError, match="must be disabled"):
        validate_runtime()


def test_aws_mode_protects_every_non_health_path(monkeypatch):
    monkeypatch.setenv("AWS_SANDBOX_MODE", "1")
    monkeypatch.setenv("LOCAL_DASHBOARD_TOKEN", "sandbox-secret")

    def request(path, token=""):
        return Request({"type": "http", "method": "GET", "path": path,
                        "headers": [(b"authorization", token.encode())]})

    require_sandbox_token(request("/health"))
    with pytest.raises(HTTPException) as exc:
        require_sandbox_token(request("/workflows/00000000-0000-0000-0000-000000000000"))
    assert exc.value.status_code == 403
    require_sandbox_token(request("/requests", "Bearer sandbox-secret"))
