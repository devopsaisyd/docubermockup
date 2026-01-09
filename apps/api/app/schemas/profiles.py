from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import Specialty, VerificationStatus


class ClinicMeOut(BaseModel):
    id: UUID
    name: str
    address: str
    city: str
    lat: float
    lng: float


class ClinicUpsertIn(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    address: str = Field(min_length=5, max_length=300)
    lat: float
    lng: float
    city: str = "Chennai"


class DoctorMeOut(BaseModel):
    id: UUID
    full_name: str
    specialty: Specialty
    reg_no: str
    verification_status: VerificationStatus
    home_lat: float | None
    home_lng: float | None
    reliability: dict


class DoctorUpsertIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=200)
    specialty: Specialty
    reg_no: str = Field(min_length=3, max_length=64)
    home_lat: float | None = None
    home_lng: float | None = None

