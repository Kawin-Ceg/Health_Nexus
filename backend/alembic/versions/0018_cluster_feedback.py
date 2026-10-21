"""community_data: whether a flagged cluster turned out to be a real outbreak

Revision ID: 0018
Revises: 0017
Create Date: 2026-10-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("community_data", sa.Column("feedback", sa.String(16), nullable=True))
    op.add_column("community_data", sa.Column("feedback_note", sa.Text(), nullable=True))
    op.add_column("community_data", sa.Column("feedback_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("community_data", sa.Column("feedback_by", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_community_data_feedback_by_users", "community_data", "users", ["feedback_by"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    op.drop_constraint("fk_community_data_feedback_by_users", "community_data", type_="foreignkey")
    for column in ("feedback_by", "feedback_at", "feedback_note", "feedback"):
        op.drop_column("community_data", column)
