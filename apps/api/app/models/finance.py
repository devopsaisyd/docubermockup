from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import CreatedAtMixin, UUIDPrimaryKeyMixin
from app.models.enums import PaymentStatus, PayoutStatus


class Payment(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "payments"
    __table_args__ = (UniqueConstraint("shift_id", name="uq_payments_shift_id"),)

    shift_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shifts.id"), nullable=False)
    clinic_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    amount_inr: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus, name="payment_status_enum"), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), default="razorpay", nullable=False)
    provider_order_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    provider_payment_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    raw_provider_payload: Mapped[str | None] = mapped_column(Text, nullable=True)

    shift: Mapped["Shift"] = relationship()


class Payout(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "payouts"
    __table_args__ = (UniqueConstraint("shift_id", name="uq_payouts_shift_id"),)

    shift_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shifts.id"), nullable=False)
    doctor_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    amount_inr: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[PayoutStatus] = mapped_column(Enum(PayoutStatus, name="payout_status_enum"), nullable=False)
    provider_payout_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    shift: Mapped["Shift"] = relationship()


from app.models.shift import Shift  # noqa: E402

