"""visit_status gains 'missed'; scheduled_visits.missed_notified_at

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE visit_status ADD VALUE IF NOT EXISTS 'missed'")

    op.add_column("scheduled_visits", sa.Column("missed_notified_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("scheduled_visits", "missed_notified_at")
    op.execute("UPDATE scheduled_visits SET status = 'scheduled' WHERE status = 'missed'")
