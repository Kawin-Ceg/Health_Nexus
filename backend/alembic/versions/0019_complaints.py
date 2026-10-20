"""concerns become complaints: who they are about, app-generated evidence, more categories;
visits: the reason a citizen gives for a missed visit

Revision ID: 0019
Revises: 0018
Create Date: 2026-10-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NEW = ("device_issue", "app_problem", "worker_conduct", "worker_no_show", "citizen_missed_visits", "citizen_conduct")


def upgrade() -> None:
    for value in NEW:
        op.execute(f"ALTER TYPE concern_category ADD VALUE IF NOT EXISTS '{value}'")
    op.add_column("concerns", sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("concerns", sa.Column("evidence", sa.JSON(), nullable=True))
    op.create_foreign_key("fk_concerns_subject_id_users", "concerns", "users", ["subject_id"], ["id"], ondelete="SET NULL")
    op.add_column("scheduled_visits", sa.Column("missed_reason", sa.Text(), nullable=True))
    op.add_column("scheduled_visits", sa.Column("missed_reason_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("scheduled_visits", "missed_reason_at")
    op.drop_column("scheduled_visits", "missed_reason")
    op.drop_constraint("fk_concerns_subject_id_users", "concerns", type_="foreignkey")
    op.drop_column("concerns", "evidence")
    op.drop_column("concerns", "subject_id")
