from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import CreatedAtMixin, UUIDPrimaryKeyMixin
from app.models.enums import AssignmentStatus, ShiftStatus, Specialty


class Shift(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "shifts"

    clinic_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    clinic_profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clinic_profiles.id"), nullable=False)

    specialty: Mapped[Specialty] = mapped_column(Enum(Specialty, name="shift_specialty_enum"), nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    pay_amount_inr: Mapped[int] = mapped_column(Integer, nullable=False)
    address: Mapped[str] = mapped_column(String(300), nullable=False)
    lat: Mapped[float] = mapped_column(nullable=False)
    lng: Mapped[float] = mapped_column(nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    auto_replace: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    status: Mapped[ShiftStatus] = mapped_column(Enum(ShiftStatus, name="shift_status_enum"), default=ShiftStatus.draft)

    clinic_user: Mapped["User"] = relationship(back_populates="clinic_shifts")
    clinic_profile: Mapped["ClinicProfile"] = relationship()
    assignment: Mapped["ShiftAssignment | None"] = relationship(back_populates="shift", uselist=False)


class ShiftAssignment(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "shift_assignments"
    __table_args__ = (UniqueConstraint("shift_id", name="uq_shift_assignments_shift_id"),)

    shift_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shifts.id"), nullable=False)
    doctor_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    doctor_profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("doctor_profiles.id"), nullable=False)

    status: Mapped[AssignmentStatus] = mapped_column(Enum(AssignmentStatus, name="assignment_status_enum"), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    shift: Mapped["Shift"] = relationship(back_populates="assignment")
    doctor_user: Mapped["User"] = relationship()
    doctor_profile: Mapped["DoctorProfile"] = relationship()

    location_pings: Mapped[list["LocationPing"]] = relationship(back_populates="assignment")
    otp_sessions: Mapped[list["OtpSession"]] = relationship(back_populates="assignment")


class LocationPing(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "location_pings"

    assignment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shift_assignments.id"), nullable=False
    )
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    lat: Mapped[float] = mapped_column(nullable=False)
    lng: Mapped[float] = mapped_column(nullable=False)
    speed: Mapped[float | None] = mapped_column(nullable=True)
    heading: Mapped[float | None] = mapped_column(nullable=True)
    accuracy: Mapped[float | None] = mapped_column(nullable=True)

    assignment: Mapped["ShiftAssignment"] = relationship(back_populates="location_pings")


class OtpSession(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "otp_sessions"

    assignment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shift_assignments.id"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(16), nullable=False)  # checkin/checkout
    otp_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    allow_remote: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    assignment: Mapped["ShiftAssignment"] = relationship(back_populates="otp_sessions")


from app.models.clinic import ClinicProfile  # noqa: E402
from app.models.doctor import DoctorProfile  # noqa: E402
from app.models.user import User  # noqa: E402

