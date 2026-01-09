from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import CreatedAtMixin, UUIDPrimaryKeyMixin


class ChatMessage(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "chat_messages"

    shift_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shifts.id"), nullable=False)
    assignment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shift_assignments.id"), nullable=True
    )
    sender_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    sender_role: Mapped[str] = mapped_column(String(32), nullable=False)

    kind: Mapped[str] = mapped_column(String(16), nullable=False, default="text")  # text|offer|system
    message: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    offer_amount_inr: Mapped[int | None] = mapped_column(Integer, nullable=True)
    offer_status: Mapped[str | None] = mapped_column(String(16), nullable=True)  # proposed|accepted|rejected

    shift: Mapped["Shift"] = relationship()


from app.models.shift import Shift  # noqa: E402

