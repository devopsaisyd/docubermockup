from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import AssignmentStatus


class AssignmentOut(BaseModel):
    id: UUID
    shift_id: UUID
    doctor_user_id: UUID
    status: AssignmentStatus
    accepted_at: datetime | None
    created_at: datetime


class AssignmentStatusUpdateIn(BaseModel):
    status: AssignmentStatus


class LocationPingIn(BaseModel):
    ts: datetime
    lat: float
    lng: float
    speed: float | None = None
    heading: float | None = None
    accuracy: float | None = None


class LiveSnapshotOut(BaseModel):
    assignment_id: UUID
    shift_id: UUID
    status: str
    tracking_active: bool
    last_ping: dict | None
    timeline: list[dict]


class OtpCreateOut(BaseModel):
    ok: bool = True
    expires_at: datetime
    dev_otp: str | None = None


class OtpVerifyIn(BaseModel):
    otp: str = Field(min_length=4, max_length=8)


class SosIn(BaseModel):
    message: str | None = Field(default=None, max_length=300)

