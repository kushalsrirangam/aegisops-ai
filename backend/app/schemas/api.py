from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class IncidentCreate(BaseModel):
    title: str = Field(min_length=5, max_length=200)
    description: str = Field(min_length=10, max_length=5000)
    service: str = Field(pattern=r"^[a-zA-Z0-9-]{2,100}$")
    evidence: dict[str, Any] = Field(default_factory=dict)

    @field_validator("evidence")
    @classmethod
    def limited_evidence(cls, value: dict[str, Any]) -> dict[str, Any]:
        import json

        if len(json.dumps(value)) > 30_000:
            raise ValueError("Evidence exceeds 30,000 characters")
        return value


class IncidentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    description: str
    service: str
    severity: str
    status: str
    mode: str
    created_at: datetime


class DecisionIn(BaseModel):
    reason: str = Field(default="", max_length=1000)


class DocumentIn(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    content: str = Field(min_length=1, max_length=100_000)
    source: str = Field(min_length=3, max_length=200)
