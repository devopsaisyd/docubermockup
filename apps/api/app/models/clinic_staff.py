from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import CreatedAtMixin, UUIDPrimaryKeyMixin


class ClinicStaffMember(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "clinic_staff_members"
    __table_args__ = (
        UniqueConstraint("clinic_user_id", "staff_user_id", name="uq_clinic_staff_members_pair"),
    )

    clinic_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    staff_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    clinic_user: Mapped["User"] = relationship(foreign_keys=[clinic_user_id])
    staff_user: Mapped["User"] = relationship(foreign_keys=[staff_user_id])


from app.models.user import User  # noqa: E402

