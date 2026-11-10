"""Planning tool contract and deterministic mock catalog."""

from typing import Protocol

from apps.api.contracts import Cloud


class ModuleCatalog(Protocol):
    def supports(self, cloud: Cloud, module: str) -> bool: ...


class MockModuleCatalog:
    def supports(self, cloud: Cloud, module: str) -> bool:
        return module == "sandbox-api" and cloud in (Cloud.AWS, Cloud.AZURE)
