import pytest

from observability.langfuse import configured_langfuse_client


def test_langfuse_config_requires_credentials_and_secure_url(monkeypatch):
    for name in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_BASE_URL"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(ValueError, match="required"):
        configured_langfuse_client()
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "public")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "secret")
    monkeypatch.setenv("LANGFUSE_BASE_URL", "http://public.example.test")
    with pytest.raises(ValueError, match="HTTPS"):
        configured_langfuse_client()
