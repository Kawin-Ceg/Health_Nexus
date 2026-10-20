"""health_records: where a reading came from (smartwatch sync, a health worker's examination, or typed in before)

Revision ID: 0015
Revises: 0014
Create Date: 2026-10-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("health_records", sa.Column("source", sa.String(16), server_default="self", nullable=False))
    op.add_column("health_records", sa.Column("recorded_by", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("health_records", sa.Column("location", sa.String(160), nullable=True))
    op.add_column("health_records", sa.Column("watch_day", sa.Date(), nullable=True))
    op.add_column("health_records", sa.Column("watch_slot", sa.String(16), nullable=True))
    op.create_foreign_key(
        "fk_health_records_recorded_by_users", "health_records", "users", ["recorded_by"], ["id"], ondelete="SET NULL"
    )
    op.create_index(
        "uq_health_records_watch_slot",
        "health_records",
        ["user_id", "watch_day", "watch_slot"],
        unique=True,
        postgresql_where=sa.text("source = 'watch'"),
    )


def downgrade() -> None:
    op.drop_index("uq_health_records_watch_slot", "health_records")
    op.drop_constraint("fk_health_records_recorded_by_users", "health_records", type_="foreignkey")
    for column in ("watch_slot", "watch_day", "location", "recorded_by", "source"):
        op.drop_column("health_records", column)
