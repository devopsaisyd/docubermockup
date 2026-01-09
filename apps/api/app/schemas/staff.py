from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class StaffInviteIn(BaseModel):
    phone: str = Field(min_length=8, max_length=20)


class StaffMemberOut(BaseModel):
    id: UUID
    phone: str | None
    created_at: datetime

