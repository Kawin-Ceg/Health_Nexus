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
    # ALTER TYPE ... ADD VALUE runs outside the migration transaction: a value
    # added inside a transaction cannot be used until that transaction commits.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE visit_status ADD VALUE IF NOT EXISTS 'missed'")

    # Makes the one-time "missed" alert idempotent.
    op.add_column("scheduled_visits", sa.Column("missed_notified_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("scheduled_visits", "missed_notified_at")
    # 'missed' stays in visit_status. Postgres cannot drop a single enum value
    # without rebuilding the type (create new type, rewrite every column that
    # uses it, drop the old one). Leaving an unused value behind is harmless,
    # and the type itself is dropped by 0001's downgrade. Rows still marked
    # 'missed' are moved back to 'scheduled' so the older code never sees it.
    op.execute("UPDATE scheduled_visits SET status = 'scheduled' WHERE status = 'missed'")
