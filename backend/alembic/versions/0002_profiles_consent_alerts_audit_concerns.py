"""user_profiles, consent_records, alerts, audit_logs, concerns

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)
TZ = sa.DateTime(timezone=True)


def enum(name: str) -> postgresql.ENUM:
    return postgresql.ENUM(name=name, create_type=False)


def upgrade() -> None:
    op.create_table(
        "user_profiles",
        sa.Column("id", UUID, nullable=False),
        sa.Column("user_id", UUID, nullable=False),
        sa.Column("age", sa.Integer(), nullable=False),
        sa.Column("gender", enum("gender"), nullable=False),
        sa.Column("height_cm", sa.Float(), nullable=False),
        sa.Column("weight_kg", sa.Float(), nullable=False),
        sa.Column("blood_group", enum("blood_group"), nullable=True),
        sa.Column("existing_conditions", sa.JSON(), server_default=sa.text("'[]'"), nullable=False),
        sa.Column("current_medications", sa.JSON(), server_default=sa.text("'[]'"), nullable=False),
        sa.Column("emergency_contact_name", sa.String(), nullable=True),
        sa.Column("emergency_contact_phone", sa.String(), nullable=True),
        sa.Column("has_smartwatch", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("smartwatch_brand", sa.String(), nullable=True),
        sa.Column("permission_health_tracking", sa.Boolean(), nullable=False),
        sa.Column("created_at", TZ, nullable=False),
        sa.Column("updated_at", TZ, nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_user_profiles"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_user_profiles_user_id_users"),
        sa.UniqueConstraint("user_id", name="uq_user_profiles_user_id"),
    )

    op.create_table(
        "consent_records",
        sa.Column("id", UUID, nullable=False),
        sa.Column("user_id", UUID, nullable=False),
        sa.Column("consent_type", enum("consent_type"), nullable=False),
        sa.Column("granted", sa.Boolean(), nullable=False),
        sa.Column("source", sa.String(), server_default=sa.text("'settings'"), nullable=False),
        sa.Column("ip_address", sa.String(), nullable=True),
        sa.Column("created_at", TZ, nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_consent_records"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_consent_records_user_id_users"),
    )
    op.create_index("ix_consent_records_user_id", "consent_records", ["user_id"])
    op.create_index("ix_consent_records_created_at", "consent_records", ["created_at"])

    op.create_table(
        "alerts",
        sa.Column("id", UUID, nullable=False),
        sa.Column("user_id", UUID, nullable=True),
        sa.Column("alert_type", enum("alert_type"), nullable=False),
        sa.Column("severity", enum("alert_severity"), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", TZ, nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_alerts"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_alerts_user_id_users"),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", UUID, nullable=False),
        sa.Column("user_id", UUID, nullable=True),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("entity", sa.String(), nullable=False),
        sa.Column("entity_id", UUID, nullable=True),
        sa.Column("ip_address", sa.String(), nullable=False),
        sa.Column("created_at", TZ, nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_audit_logs"),
    )

    op.create_table(
        "concerns",
        sa.Column("id", UUID, nullable=False),
        sa.Column("ticket_ref", sa.String(16), nullable=False),
        sa.Column("user_id", UUID, nullable=False),
        sa.Column("category", enum("concern_category"), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("attachment_url", sa.String(), nullable=True),
        sa.Column("status", enum("concern_status"), server_default=sa.text("'open'"), nullable=False),
        sa.Column("admin_note", sa.Text(), nullable=True),
        sa.Column("handled_by", UUID, nullable=True),
        sa.Column("created_at", TZ, nullable=False),
        sa.Column("updated_at", TZ, nullable=False),
        sa.Column("resolved_at", TZ, nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_concerns"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_concerns_user_id_users"),
        sa.ForeignKeyConstraint(["handled_by"], ["users.id"], name="fk_concerns_handled_by_users"),
        sa.UniqueConstraint("ticket_ref", name="uq_concerns_ticket_ref"),
    )
    op.create_index("ix_concerns_user_id", "concerns", ["user_id"])
    op.create_index("ix_concerns_status", "concerns", ["status"])


def downgrade() -> None:
    op.drop_table("concerns")
    op.drop_table("audit_logs")
    op.drop_table("alerts")
    op.drop_table("consent_records")
    op.drop_table("user_profiles")
