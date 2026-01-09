"""chat + clinic staff members

Revision ID: 0002_chat_staff
Revises: 0001_init
Create Date: 2026-01-09

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0002_chat_staff"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "clinic_staff_members",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("clinic_user_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("staff_user_id", sa.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["clinic_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["staff_user_id"], ["users.id"]),
        sa.UniqueConstraint("clinic_user_id", "staff_user_id", name="uq_clinic_staff_members_pair"),
    )

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("shift_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("assignment_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("sender_user_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("sender_role", sa.String(length=32), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False, server_default="text"),
        sa.Column("message", sa.String(length=1000), nullable=True),
        sa.Column("offer_amount_inr", sa.Integer(), nullable=True),
        sa.Column("offer_status", sa.String(length=16), nullable=True),
        sa.ForeignKeyConstraint(["shift_id"], ["shifts.id"]),
        sa.ForeignKeyConstraint(["assignment_id"], ["shift_assignments.id"]),
        sa.ForeignKeyConstraint(["sender_user_id"], ["users.id"]),
    )


def downgrade() -> None:
    op.drop_table("chat_messages")
    op.drop_table("clinic_staff_members")

