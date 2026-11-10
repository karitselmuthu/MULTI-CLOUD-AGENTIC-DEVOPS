"""Week 1 request and response contracts.

Sources: https://fastapi.tiangolo.com/tutorial/body/
         https://pydantic.dev/docs/validation/latest/concepts/fields/
"""

from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Cloud(StrEnum):
    AWS = "aws"
    AZURE = "azure"


class Environment(StrEnum):
    SANDBOX = "sandbox"
    DEV = "dev"
    STAGING = "staging"
    PROD = "prod"


class Application(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=63, pattern=r"^[a-z][a-z0-9-]*[a-z0-9]$")
    repository: str = Field(min_length=1, max_length=256)


class Infrastructure(BaseModel):
    model_config = ConfigDict(extra="forbid")

    region: str = Field(min_length=2, max_length=64)
    module: str = Field(min_length=1, max_length=128)


class ApprovalIntent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    required: Literal[True]
    change_record: str | None = Field(default=None, max_length=128)


class RequestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cloud: Cloud
    environment: Environment
    requester: str = Field(min_length=3, max_length=128)
    application: Application
    infrastructure: Infrastructure
    approval: ApprovalIntent

    @field_validator("requester")
    @classmethod
    def requester_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("requester must not be blank")
        return value


class WorkflowResponse(BaseModel):
    id: UUID
    status: Literal["received"]
    cloud: Cloud
    environment: Environment
    created_at: datetime
    request_digest: str


class HealthResponse(BaseModel):
    status: Literal["ok"]
