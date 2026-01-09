from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ChatMessageOut(BaseModel):
    id: UUID
    shift_id: UUID
    assignment_id: UUID | None
    sender_user_id: UUID
    sender_role: str
    kind: str
    message: str | None
    offer_amount_inr: int | None
    offer_status: str | None
    created_at: datetime


class ChatSendIn(BaseModel):
    kind: str = Field(default="text", description="text|offer")
    message: str | None = Field(default=None, max_length=1000)
    offer_amount_inr: int | None = Field(default=None, ge=100, le=200000)


class OfferRespondIn(BaseModel):
    action: str = Field(description="accept|reject")

