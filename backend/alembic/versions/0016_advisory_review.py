"""advisories: the reason given for a red advisory, and the admin's review of how it went

Revision ID: 0016
Revises: 0015
Create Date: 2026-10-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("advisories", sa.Column("red_reason", sa.Text(), nullable=True))
    op.add_column("advisories", sa.Column("feedback", sa.String(8), nullable=True))
    op.add_column("advisories", sa.Column("feedback_note", sa.Text(), nullable=True))
    op.add_column("advisories", sa.Column("feedback_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    for column in ("feedback_at", "feedback_note", "feedback", "red_reason"):
        op.drop_column("advisories", column)
