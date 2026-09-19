"""phc_applications, phc_verification_documents, phc_verification_audit_log

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)
TZ = sa.DateTime(timezone=True)


def enum(name: str) -> postgresql.ENUM:
    return postgresql.ENUM(name=name, create_type=False)


def upgrade() -> None:
    op.create_table(
        "phc_applications",
        sa.Column("id", UUID, nullable=False),
        sa.Column("user_id", UUID, nullable=False),
        sa.Column("employee_id", sa.String(), nullable=False),
        sa.Column("designation", enum("designation"), nullable=False),
        sa.Column("phc_name", sa.String(), nullable=False),
        sa.Column("district", sa.String(), nullable=False),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("years_of_service", sa.Integer(), nullable=False),
        sa.Column("status", enum("application_status"), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("rejection_reason", sa.String(), nullable=True),
        sa.Column("facility_id", UUID, nullable=True),
        sa.Column("last_checked_at", TZ, nullable=True),
        sa.Column("reviewed_by", UUID, nullable=True),
        sa.Column("reviewed_at", TZ, nullable=True),
        sa.Column("created_at", TZ, nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_phc_applications"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_phc_applications_user_id_users"),
        sa.ForeignKeyConstraint(
            ["facility_id"], ["valid_phc_facilities.id"], name="fk_phc_applications_facility_id_valid_phc_facilities"
        ),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], name="fk_phc_applications_reviewed_by_users"),
        sa.UniqueConstraint("user_id", name="uq_phc_applications_user_id"),
    )

    op.create_table(
        "phc_verification_documents",
        sa.Column("id", UUID, nullable=False),
        sa.Column("application_id", UUID, nullable=False),
        sa.Column("user_id", UUID, nullable=False),
        sa.Column("document_type", enum("phc_document_type"), nullable=False),
        sa.Column("storage_key", sa.String(), nullable=False),
        sa.Column("content_type", sa.String(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("original_filename", sa.String(), nullable=True),
        sa.Column("status", enum("phc_document_status"), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("ocr_text", sa.Text(), nullable=True),
        sa.Column("extracted_registration_no", sa.String(), nullable=True),
        sa.Column("tamper_score", sa.Integer(), nullable=True),
        sa.Column("check_notes", sa.Text(), nullable=True),
        sa.Column("checked_at", TZ, nullable=True),
        sa.Column("uploaded_at", TZ, nullable=False),
        sa.Column("deleted_at", TZ, nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_phc_verification_documents"),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["phc_applications.id"],
            name="fk_phc_verification_documents_application_id_phc_applications",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_phc_verification_documents_user_id_users"),
    )
    op.create_index(
        "ix_phc_verification_documents_application_id", "phc_verification_documents", ["application_id"]
    )
    op.create_index("ix_phc_verification_documents_user_id", "phc_verification_documents", ["user_id"])
    op.create_index("ix_phc_verification_documents_sha256", "phc_verification_documents", ["sha256"])

    op.create_table(
        "phc_verification_audit_log",
        sa.Column("id", UUID, nullable=False),
        sa.Column("application_id", UUID, nullable=False),
        sa.Column("subject_user_id", UUID, nullable=False),
        sa.Column("actor_user_id", UUID, nullable=True),
        sa.Column("document_id", UUID, nullable=True),
        sa.Column("action", enum("phc_verification_action"), nullable=False),
        sa.Column("from_status", sa.String(32), nullable=True),
        sa.Column("to_status", sa.String(32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("auto_check_summary", sa.Text(), nullable=True),
        sa.Column("override_reason", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(), server_default=sa.text("'unknown'"), nullable=False),
        sa.Column("created_at", TZ, nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_phc_verification_audit_log"),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["phc_applications.id"],
            name="fk_phc_verification_audit_log_application_id_phc_applications",
        ),
        sa.ForeignKeyConstraint(
            ["subject_user_id"], ["users.id"], name="fk_phc_verification_audit_log_subject_user_id_users"
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"], ["users.id"], name="fk_phc_verification_audit_log_actor_user_id_users"
        ),
    )
    op.create_index(
        "ix_phc_verification_audit_log_application_id", "phc_verification_audit_log", ["application_id"]
    )
    op.create_index(
        "ix_phc_verification_audit_log_subject_user_id", "phc_verification_audit_log", ["subject_user_id"]
    )
    op.create_index("ix_phc_verification_audit_log_actor_user_id", "phc_verification_audit_log", ["actor_user_id"])
    op.create_index("ix_phc_verification_audit_log_created_at", "phc_verification_audit_log", ["created_at"])


def downgrade() -> None:
    op.drop_table("phc_verification_audit_log")
    op.drop_table("phc_verification_documents")
    op.drop_table("phc_applications")
