from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import CreatedAtMixin, UUIDPrimaryKeyMixin
from app.models.enums import Role


class User(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("phone", name="uq_users_phone"),
        UniqueConstraint("email", name="uq_users_email"),
    )

    role: Mapped[Role] = mapped_column(Enum(Role, name="role_enum"), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    clinic_profile: Mapped["ClinicProfile | None"] = relationship(back_populates="user", uselist=False)
    doctor_profile: Mapped["DoctorProfile | None"] = relationship(back_populates="user", uselist=False)

    clinic_shifts: Mapped[list["Shift"]] = relationship(back_populates="clinic_user")


class AuthOtp(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "auth_otps"
    __table_args__ = (UniqueConstraint("phone", name="uq_auth_otps_phone"),)

    phone: Mapped[str] = mapped_column(String(32), nullable=False)
    otp_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


from app.models.clinic import ClinicProfile  # noqa: E402
from app.models.doctor import DoctorProfile  # noqa: E402
from app.models.shift import Shift  # noqa: E402

