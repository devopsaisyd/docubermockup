from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import CreatedAtMixin, UUIDPrimaryKeyMixin
from app.models.enums import Specialty, VerificationStatus


class DoctorProfile(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "doctor_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    specialty: Mapped[Specialty] = mapped_column(Enum(Specialty, name="specialty_enum"), nullable=False)
    reg_no: Mapped[str] = mapped_column(String(64), nullable=False)
    verification_status: Mapped[VerificationStatus] = mapped_column(
        Enum(VerificationStatus, name="verification_status_enum"),
        default=VerificationStatus.pending,
        nullable=False,
    )
    home_lat: Mapped[float | None] = mapped_column(nullable=True)
    home_lng: Mapped[float | None] = mapped_column(nullable=True)

    reliability_cancels_count: Mapped[int] = mapped_column(default=0, nullable=False)
    reliability_no_show_count: Mapped[int] = mapped_column(default=0, nullable=False)
    reliability_on_time_rate: Mapped[float] = mapped_column(default=0.85, nullable=False)
    reliability_avg_rating: Mapped[float] = mapped_column(default=4.5, nullable=False)

    user: Mapped["User"] = relationship(back_populates="doctor_profile")
    credentials: Mapped[list["Credential"]] = relationship(back_populates="doctor")


class Credential(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "credentials"

    doctor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("doctor_profiles.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(nullable=True)

    doctor: Mapped["DoctorProfile"] = relationship(back_populates="credentials")


from app.models.user import User  # noqa: E402

