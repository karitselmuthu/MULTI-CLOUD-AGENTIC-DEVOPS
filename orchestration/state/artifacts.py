"""Tenant-scoped local artifact adapter; workflow metadata stays in PostgreSQL."""

import hashlib
import io
import re
from pathlib import Path


SAFE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,127}$")


class LocalArtifactStore:
    def __init__(self, root: Path):
        self.root = root

    def _path(self, tenant: str, workflow_id: str, name: str) -> Path:
        if not all(SAFE.fullmatch(part) for part in (tenant, workflow_id, name)):
            raise ValueError("invalid artifact key")
        return self.root / tenant / workflow_id / name

    def put(self, tenant: str, workflow_id: str, name: str, content: bytes) -> str:
        path = self._path(tenant, workflow_id, name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return hashlib.sha256(content).hexdigest()

    def get(self, tenant: str, workflow_id: str, name: str) -> bytes:
        return self._path(tenant, workflow_id, name).read_bytes()


class MinioArtifactStore:
    """S3-compatible object adapter; bucket/IAM policy must enforce the same scope.

    Source: https://docs.min.io/aistor/developers/sdk/python/api/#put_object
    """

    def __init__(self, client, bucket: str):
        if not bucket:
            raise ValueError("artifact bucket required")
        self.client = client
        self.bucket = bucket

    def _key(self, tenant: str, workflow_id: str, name: str) -> str:
        if not all(SAFE.fullmatch(part) for part in (tenant, workflow_id, name)):
            raise ValueError("invalid artifact key")
        return f"{tenant}/{workflow_id}/{name}"

    def put(self, tenant: str, workflow_id: str, name: str, content: bytes) -> str:
        key = self._key(tenant, workflow_id, name)
        digest = hashlib.sha256(content).hexdigest()
        self.client.put_object(self.bucket, key, io.BytesIO(content), len(content),
                               metadata={"sha256": digest})
        return digest

    def get(self, tenant: str, workflow_id: str, name: str) -> bytes:
        response = self.client.get_object(self.bucket, self._key(tenant, workflow_id, name))
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()
