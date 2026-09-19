"""Enums, users, refresh_tokens

Every Postgres ENUM is created here, once. Later migrations bind to them with
postgresql.ENUM(..., create_type=False).

Revision ID: 0001
Revises:
Create Date: 2026-09-20
"""

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ENUMS: dict[str, tuple[str, ...]] = {
    "user_role": ("user", "pending_phc", "phc_worker", "admin"),
    "gender": ("male", "female", "other", "prefer_not_to_say"),
    "blood_group": ("A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"),
    "designation": (
        "medical_officer",
        "staff_nurse",
        "health_inspector",
        "asha_supervisor",
        "block_health_supervisor",
    ),
    "application_status": ("pending", "approved", "rejected"),
    "phc_document_type": ("employee_id_card", "appointment_order", "registration_certificate"),
    "phc_document_status": ("pending", "auto_passed", "flagged", "rejected", "accepted"),
    "phc_verification_action": (
        "application_approved",
        "application_rejected",
        "application_revoked",
        "document_accepted",
        "document_rejected",
    ),
    "alert_type": ("personal", "community"),
    "alert_severity": ("low", "medium", "high"),
    "flag_resolution": ("reviewed", "dismissed"),
    "flag_dismiss_reason": ("false_positive", "already_treated", "contacted", "other"),
    # 'missed' is added by migration 0008.
    "visit_status": ("scheduled", "completed", "cancelled"),
    "concern_category": ("data_misuse", "incorrect_diagnosis_flag", "harassment", "access_request", "other"),
    "concern_status": ("open", "in_review", "resolved", "rejected"),
    "consent_type": (
        "community_surveillance",
        "health_tracking",
        "phc_worker_access",
        "research_analytics",
        "marketing_updates",
    ),
    "chat_message_role": ("user", "assistant"),
    "chat_refusal_reason": ("insufficient_history", "out_of_scope", "no_matching_records", "error"),
}

DEFAULT_PREFERENCES = {
    "theme": "system",
    "language": "en",
    "notifications": {
        "alerts": {"email": True, "sms": False, "in_app": True},
        "surveillance": {"email": False, "sms": False, "in_app": True},
        "announcements": {"email": True, "sms": False, "in_app": True},
    },
    "alert_threshold": 70,
    "working_hours": {"start": "09:00", "end": "17:00"},
    "resubmission_reminders": True,
}

UUID = postgresql.UUID(as_uuid=True)
TZ = sa.DateTime(timezone=True)


def upgrade() -> None:
    # Step 1: enum types
    bind = op.get_bind()
    for name, values in ENUMS.items():
        postgresql.ENUM(*values, name=name).create(bind, checkfirst=False)

    # Step 2: tables
    op.create_table(
        "users",
        sa.Column("id", UUID, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column(
            "role",
            postgresql.ENUM(name="user_role", create_type=False),
            server_default=sa.text("'user'"),
            nullable=False,
        ),
        sa.Column("consent", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("profile_completed", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("avatar_url", sa.String(), nullable=True),
        sa.Column("cover_url", sa.String(), nullable=True),
        sa.Column("bio", sa.String(280), nullable=True),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("location", sa.String(), nullable=True),
        sa.Column("department", sa.String(), nullable=True),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("is_verified", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("verified_at", TZ, nullable=True),
        sa.Column("verification_token_hash", sa.String(), nullable=True),
        sa.Column("verification_token_expires_at", TZ, nullable=True),
        sa.Column("verification_sent_at", TZ, nullable=True),
        sa.Column("verification_deadline", TZ, nullable=True),
        sa.Column("email_verified", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("pending_email", sa.String(), nullable=True),
        sa.Column("email_token_hash", sa.String(), nullable=True),
        sa.Column("email_token_expires_at", TZ, nullable=True),
        sa.Column(
            "preferences",
            sa.JSON(),
            server_default=sa.text(f"'{json.dumps(DEFAULT_PREFERENCES)}'"),
            nullable=False,
        ),
        sa.Column("deactivated_at", TZ, nullable=True),
        sa.Column("created_at", TZ, nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_verification_token_hash", "users", ["verification_token_hash"])

    op.create_table(
        "refresh_tokens",
        sa.Column("id", UUID, nullable=False),
        sa.Column("user_id", UUID, nullable=False),
        sa.Column("token_hash", sa.String(), nullable=False),
        sa.Column("expires_at", TZ, nullable=False),
        sa.Column("revoked", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", TZ, nullable=False),
        sa.Column("last_activity_at", TZ, nullable=False),
        sa.Column("revoked_at", TZ, nullable=True),
        sa.Column("revoked_reason", sa.String(), nullable=True),
        sa.Column("user_agent", sa.String(), nullable=True),
        sa.Column("ip_address", sa.String(), nullable=True),
        sa.Column("device_label", sa.String(), nullable=True),
        sa.Column("rotated_from", UUID, nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_refresh_tokens"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_refresh_tokens_user_id_users"),
        sa.ForeignKeyConstraint(
            ["rotated_from"], ["refresh_tokens.id"], name="fk_refresh_tokens_rotated_from_refresh_tokens"
        ),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"], unique=True)


def downgrade() -> None:
    op.drop_table("refresh_tokens")
    op.drop_table("users")
    bind = op.get_bind()
    for name in reversed(list(ENUMS)):
        postgresql.ENUM(name=name).drop(bind, checkfirst=False)
