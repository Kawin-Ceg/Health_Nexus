"""scheduled_visits: kind of visit, length, notes, and who cancelled it and why

Revision ID: 0020
Revises: 0019
Create Date: 2026-10-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0020"
down_revision: str | None = "0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

COLUMNS = ("visit_type", "duration_minutes", "notes", "cancelled_by", "cancel_reason", "cancelled_at")


def upgrade() -> None:
    op.add_column("scheduled_visits", sa.Column("visit_type", sa.String(24), server_default="home", nullable=False))
    op.add_column("scheduled_visits", sa.Column("duration_minutes", sa.Integer(), server_default="30", nullable=False))
    op.add_column("scheduled_visits", sa.Column("notes", sa.Text(), nullable=True))
    op.add_column("scheduled_visits", sa.Column("cancelled_by", sa.String(16), nullable=True))
    op.add_column("scheduled_visits", sa.Column("cancel_reason", sa.Text(), nullable=True))
    op.add_column("scheduled_visits", sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    for column in reversed(COLUMNS):
        op.drop_column("scheduled_visits", column)
