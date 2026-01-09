from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ApiBase(BaseModel):
    model_config = {"from_attributes": True}


class IdRef(ApiBase):
    id: UUID


class Timestamped(ApiBase):
    created_at: datetime


class MoneyINR(BaseModel):
    amount_inr: int = Field(ge=100, le=200000)

