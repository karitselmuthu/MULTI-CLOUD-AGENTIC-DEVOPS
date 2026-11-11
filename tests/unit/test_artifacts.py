import pytest

from orchestration.state.artifacts import LocalArtifactStore, MinioArtifactStore
from orchestration.state.cache import RedisContextCache


def test_artifacts_are_scoped_and_content_addressable(tmp_path):
    store = LocalArtifactStore(tmp_path)
    digest = store.put("team-a", "workflow-1", "plan", b"saved plan")
    assert len(digest) == 64
    assert store.get("team-a", "workflow-1", "plan") == b"saved plan"
    with pytest.raises(FileNotFoundError):
        store.get("team-b", "workflow-1", "plan")
    with pytest.raises(ValueError):
        store.put("../team-b", "workflow-1", "plan", b"bad")


def test_minio_artifact_adapter_uses_tenant_prefix():
    class Response:
        def read(self): return b"plan"
        def close(self): pass
        def release_conn(self): pass
    class Client:
        def put_object(self, bucket, key, stream, length, metadata):
            assert (bucket, key, stream.read(), length) == ("artifacts", "team-a/workflow-1/plan", b"plan", 4)
            assert len(metadata["sha256"]) == 64
        def get_object(self, bucket, key):
            assert (bucket, key) == ("artifacts", "team-a/workflow-1/plan")
            return Response()
    store = MinioArtifactStore(Client(), "artifacts")
    assert len(store.put("team-a", "workflow-1", "plan", b"plan")) == 64
    assert store.get("team-a", "workflow-1", "plan") == b"plan"


def test_redis_cache_is_scoped_and_expires():
    class Client:
        def __init__(self): self.values = {}
        def set(self, key, value, ex):
            assert ex == 60
            self.values[key] = value
        def get(self, key): return self.values.get(key)
    cache = RedisContextCache(Client(), 60)
    cache.put("team-a", "module-doc", b"summary")
    assert cache.get("team-a", "module-doc") == b"summary"
    assert cache.get("team-b", "module-doc") is None
