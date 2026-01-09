"""initial schema

Revision ID: 0001_init
Revises: 
Create Date: 2026-01-09

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    role_enum = sa.Enum("clinic_admin", "clinic_staff", "doctor", "admin", name="role_enum")
    specialty_enum = sa.Enum("dentist_general", "endodontist", "anesthetist", name="specialty_enum")
    verification_enum = sa.Enum("pending", "approved", "rejected", name="verification_status_enum")
    shift_status_enum = sa.Enum(
        "draft",
        "posted",
        "booked",
        "en_route",
        "checked_in",
        "completed",
        "paid",
        "canceled",
        "no_show",
        name="shift_status_enum",
    )
    assignment_status_enum = sa.Enum(
        "booked",
        "en_route",
        "checked_in",
        "completed",
        "canceled",
        "no_show",
        name="assignment_status_enum",
    )
    shift_specialty_enum = sa.Enum("dentist_general", "endodontist", "anesthetist", name="shift_specialty_enum")
    payment_status_enum = sa.Enum("created", "paid", "failed", name="payment_status_enum")
    payout_status_enum = sa.Enum("pending", "processing", "paid", "failed", name="payout_status_enum")

    role_enum.create(op.get_bind(), checkfirst=True)
    specialty_enum.create(op.get_bind(), checkfirst=True)
    verification_enum.create(op.get_bind(), checkfirst=True)
    shift_status_enum.create(op.get_bind(), checkfirst=True)
    assignment_status_enum.create(op.get_bind(), checkfirst=True)
    shift_specialty_enum.create(op.get_bind(), checkfirst=True)
    payment_status_enum.create(op.get_bind(), checkfirst=True)
    payout_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("role", role_enum, nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("phone", name="uq_users_phone"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    op.create_table(
        "clinic_profiles",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("address", sa.String(length=300), nullable=False),
        sa.Column("city", sa.String(length=64), nullable=False, server_default="Chennai"),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lng", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )

    op.create_table(
        "doctor_profiles",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("specialty", specialty_enum, nullable=False),
        sa.Column("reg_no", sa.String(length=64), nullable=False),
        sa.Column("verification_status", verification_enum, nullable=False, server_default="pending"),
        sa.Column("home_lat", sa.Float(), nullable=True),
        sa.Column("home_lng", sa.Float(), nullable=True),
        sa.Column("reliability_cancels_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reliability_no_show_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reliability_on_time_rate", sa.Float(), nullable=False, server_default="0.85"),
        sa.Column("reliability_avg_rating", sa.Float(), nullable=False, server_default="4.5"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )

    op.create_table(
        "credentials",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("doctor_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("file_url", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["doctor_id"], ["doctor_profiles.id"]),
    )

    op.create_table(
        "shifts",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("clinic_user_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_profile_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("specialty", shift_specialty_enum, nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("pay_amount_inr", sa.Integer(), nullable=False),
        sa.Column("address", sa.String(length=300), nullable=False),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lng", sa.Float(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("auto_replace", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("status", shift_status_enum, nullable=False, server_default="draft"),
        sa.ForeignKeyConstraint(["clinic_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["clinic_profile_id"], ["clinic_profiles.id"]),
    )

    op.create_table(
        "shift_assignments",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("shift_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("doctor_user_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("doctor_profile_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("status", assignment_status_enum, nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["shift_id"], ["shifts.id"]),
        sa.ForeignKeyConstraint(["doctor_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["doctor_profile_id"], ["doctor_profiles.id"]),
        sa.UniqueConstraint("shift_id", name="uq_shift_assignments_shift_id"),
    )

    op.create_table(
        "location_pings",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("assignment_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lng", sa.Float(), nullable=False),
        sa.Column("speed", sa.Float(), nullable=True),
        sa.Column("heading", sa.Float(), nullable=True),
        sa.Column("accuracy", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["assignment_id"], ["shift_assignments.id"]),
    )

    op.create_table(
        "otp_sessions",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("assignment_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.String(length=16), nullable=False),
        sa.Column("otp_hash", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("allow_remote", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.ForeignKeyConstraint(["assignment_id"], ["shift_assignments.id"]),
    )

    op.create_table(
        "payments",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("shift_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_user_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("amount_inr", sa.Integer(), nullable=False),
        sa.Column("status", payment_status_enum, nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False, server_default="razorpay"),
        sa.Column("provider_order_id", sa.String(length=128), nullable=True),
        sa.Column("provider_payment_id", sa.String(length=128), nullable=True),
        sa.Column("raw_provider_payload", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["shift_id"], ["shifts.id"]),
        sa.ForeignKeyConstraint(["clinic_user_id"], ["users.id"]),
        sa.UniqueConstraint("shift_id", name="uq_payments_shift_id"),
    )

    op.create_table(
        "payouts",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("shift_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("doctor_user_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("amount_inr", sa.Integer(), nullable=False),
        sa.Column("status", payout_status_enum, nullable=False),
        sa.Column("provider_payout_id", sa.String(length=128), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["shift_id"], ["shifts.id"]),
        sa.ForeignKeyConstraint(["doctor_user_id"], ["users.id"]),
        sa.UniqueConstraint("shift_id", name="uq_payouts_shift_id"),
    )

    op.create_table(
        "ratings",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("shift_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_user_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("doctor_user_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("stars", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["shift_id"], ["shifts.id"]),
        sa.ForeignKeyConstraint(["clinic_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["doctor_user_id"], ["users.id"]),
        sa.UniqueConstraint("shift_id", name="uq_ratings_shift_id"),
    )

    op.create_table(
        "audit_events",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("shift_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("assignment_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_user_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.ForeignKeyConstraint(["shift_id"], ["shifts.id"]),
        sa.ForeignKeyConstraint(["assignment_id"], ["shift_assignments.id"]),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
    )

    op.create_table(
        "auth_otps",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=False),
        sa.Column("otp_hash", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("phone", name="uq_auth_otps_phone"),
    )


def downgrade() -> None:
    op.drop_table("auth_otps")
    op.drop_table("audit_events")
    op.drop_table("ratings")
    op.drop_table("payouts")
    op.drop_table("payments")
    op.drop_table("otp_sessions")
    op.drop_table("location_pings")
    op.drop_table("shift_assignments")
    op.drop_table("shifts")
    op.drop_table("credentials")
    op.drop_table("doctor_profiles")
    op.drop_table("clinic_profiles")
    op.drop_table("users")

    op.execute("DROP TYPE IF EXISTS payout_status_enum")
    op.execute("DROP TYPE IF EXISTS payment_status_enum")
    op.execute("DROP TYPE IF EXISTS shift_specialty_enum")
    op.execute("DROP TYPE IF EXISTS assignment_status_enum")
    op.execute("DROP TYPE IF EXISTS shift_status_enum")
    op.execute("DROP TYPE IF EXISTS verification_status_enum")
    op.execute("DROP TYPE IF EXISTS specialty_enum")
    op.execute("DROP TYPE IF EXISTS role_enum")

