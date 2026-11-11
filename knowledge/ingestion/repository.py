"""Ingest only explicitly listed repository Markdown sources."""

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Protocol


@dataclass(frozen=True)
class ApprovedSource:
    path: str
    tenant: str
    roles: tuple[str, ...]
    revision: str
    approved_by: str


class DocumentSink(Protocol):
    def approve(self, document) -> None: ...


class RepositoryIngestor:
    def __init__(self, root: Path, sink: DocumentSink, allowed_paths: Iterable[str]):
        self.root = root.resolve()
        self.sink = sink
        self.allowed_paths = frozenset(allowed_paths)
        if not self.allowed_paths:
            raise ValueError("repository ingestion needs an explicit allowlist")

    def ingest(self, source: ApprovedSource) -> None:
        if source.path not in self.allowed_paths:
            raise PermissionError("source is not allowlisted")
        if not all((source.path, source.tenant, source.roles, source.revision, source.approved_by)):
            raise ValueError("approved source metadata is incomplete")
        path = (self.root / source.path).resolve()
        if not path.is_relative_to(self.root) or path.suffix.lower() != ".md" or not path.is_file():
            raise ValueError("source must be a repository Markdown file")
        from knowledge.retrieval.qdrant import ApprovedDocument

        self.sink.approve(ApprovedDocument(
            source=f"repo://{path.relative_to(self.root).as_posix()}",
            title=path.stem.replace("-", " ").title(), content=path.read_text(),
            tenant=source.tenant, roles=source.roles, revision=source.revision,
            approved_by=source.approved_by,
        ))
