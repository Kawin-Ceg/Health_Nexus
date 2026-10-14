"""advisories: community health notices with an author, an audience and an expiry

Existing community alerts (user_id IS NULL) move here as statewide notices.

Revision ID: 0013
Revises: 0012
Create Date: 2026-10-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)
TZ = sa.DateTime(timezone=True)
SCOPE = postgresql.ENUM("centre", "district", "state", name="advisory_scope")


def upgrade() -> None:
    SCOPE.create(op.get_bind())
    op.create_table(
        "advisories",
        sa.Column("id", UUID, nullable=False),
        sa.Column("author_id", UUID, nullable=True),
        sa.Column("scope", postgresql.ENUM(name="advisory_scope", create_type=False), nullable=False),
        sa.Column("phc_id", UUID, nullable=True),
        sa.Column("district", sa.String(), nullable=True),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("severity", postgresql.ENUM(name="alert_severity", create_type=False), nullable=False),
        sa.Column("expires_at", TZ, nullable=False),
        sa.Column("withdrawn_at", TZ, nullable=True),
        sa.Column("created_at", TZ, nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_advisories"),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], name="fk_advisories_author_id_users", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["phc_id"], ["valid_phc_facilities.id"], name="fk_advisories_phc_id_valid_phc_facilities"),
        sa.CheckConstraint(
            "(scope = 'centre' AND phc_id IS NOT NULL) OR (scope = 'district' AND district IS NOT NULL) OR scope = 'state'",
            name="ck_advisories_audience",
        ),
    )
    op.create_index("ix_advisories_author_id", "advisories", ["author_id"])
    op.create_index("ix_advisories_phc_id", "advisories", ["phc_id"])
    op.create_index("ix_advisories_district", "advisories", ["district"])
    op.create_index("ix_advisories_expires_at", "advisories", ["expires_at"])

    op.execute(
        """
        INSERT INTO advisories (id, scope, state, title, body, severity, expires_at, created_at)
        SELECT id, 'state', 'Tamil Nadu', 'Health advisory', message, severity,
               created_at + interval '30 days', created_at
        FROM alerts WHERE alert_type = 'community' AND user_id IS NULL
        """
    )
    op.execute("DELETE FROM alerts WHERE alert_type = 'community' AND user_id IS NULL")


def downgrade() -> None:
    op.execute(
        """
        INSERT INTO alerts (id, user_id, alert_type, severity, message, is_read, created_at)
        SELECT id, NULL, 'community', severity, body, false, created_at FROM advisories
        """
    )
    op.drop_table("advisories")
    SCOPE.drop(op.get_bind())
