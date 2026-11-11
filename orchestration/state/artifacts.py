"""Compatibility imports; artifact adapters live under data.object_storage."""

from data.object_storage.adapters import LocalArtifactStore, MinioArtifactStore

__all__ = ["LocalArtifactStore", "MinioArtifactStore"]
