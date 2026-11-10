"""Narrow model gateway contract; mock implementation makes no network calls."""

from typing import Protocol

from apps.api.contracts import RequestCreate


class ModelGateway(Protocol):
    def propose(self, request: RequestCreate) -> dict: ...


class MockModelGateway:
    def propose(self, request: RequestCreate) -> dict:
        return {
            "cloud": request.cloud.value,
            "environment": request.environment.value,
            "application": request.application.name,
            "action": "simulate",
        }
