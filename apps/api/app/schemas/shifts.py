from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import ShiftStatus, Specialty


class ShiftCreateIn(BaseModel):
    specialty: Specialty
    start_time: datetime
    end_time: datetime
    pay_amount_inr: int = Field(ge=100, le=200000)
    address: str = Field(min_length=5, max_length=300)
    lat: float
    lng: float
    notes: str | None = Field(default=None, max_length=1000)
    auto_replace: bool = False


class ShiftOut(BaseModel):
    id: UUID
    clinic_profile_id: UUID
    specialty: Specialty
    start_time: datetime
    end_time: datetime
    pay_amount_inr: int
    address: str
    lat: float
    lng: float
    notes: str | None
    auto_replace: bool
    status: ShiftStatus
    created_at: datetime
    assignment_id: UUID | None = None
    doctor_user_id: UUID | None = None
    doctor_name: str | None = None


class CandidateOut(BaseModel):
    doctor_user_id: UUID
    doctor_profile_id: UUID
    full_name: str
    specialty: str
    reliability: dict
    eta_minutes: int | None
    distance_m: int


class ShiftBookIn(BaseModel):
    doctor_user_id: UUID | None = Field(
        default=None,
        description="Clinic-driven booking: choose a doctor. Doctor-driven accept can omit this.",
    )


class BookResultOut(BaseModel):
    shift_id: UUID
    assignment_id: UUID
    status: str

