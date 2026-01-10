"""push tokens

Revision ID: 0003_push_tokens
Revises: 0002_chat_staff
Create Date: 2026-01-09

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0003_push_tokens"
down_revision = "0002_chat_staff"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "push_tokens",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("token", sa.String(length=255), nullable=False),
        sa.Column("platform", sa.String(length=32), nullable=False, server_default="expo"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.UniqueConstraint("token", name="uq_push_tokens_token"),
    )


def downgrade() -> None:
    op.drop_table("push_tokens")

