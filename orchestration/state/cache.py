"""Optional tenant-scoped cache. It never owns workflow or approval state.

Source: https://redis.io/docs/latest/develop/clients/redis-py/
"""

from orchestration.state.artifacts import SAFE


class RedisContextCache:
    def __init__(self, client, ttl_seconds: int = 300):
        if not 1 <= ttl_seconds <= 3600:
            raise ValueError("cache TTL must be between 1 and 3600 seconds")
        self.client = client
        self.ttl_seconds = ttl_seconds

    def _key(self, tenant: str, key: str) -> str:
        if not SAFE.fullmatch(tenant) or not SAFE.fullmatch(key):
            raise ValueError("invalid cache key")
        return f"context:{tenant}:{key}"

    def get(self, tenant: str, key: str) -> bytes | None:
        return self.client.get(self._key(tenant, key))

    def put(self, tenant: str, key: str, value: bytes) -> None:
        self.client.set(self._key(tenant, key), value, ex=self.ttl_seconds)
