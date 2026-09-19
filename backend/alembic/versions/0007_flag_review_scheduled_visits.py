"""processed_data review/resolution columns; scheduled_visits

An open flag is `is_anomaly = true AND resolution IS NULL`.

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)
TZ = sa.DateTime(timezone=True)


def enum(name: str) -> postgresql.ENUM:
    return postgresql.ENUM(name=name, create_type=False)


def upgrade() -> None:
    op.add_column("processed_data", sa.Column("reviewed_at", TZ, nullable=True))
    op.add_column("processed_data", sa.Column("reviewed_by", UUID, nullable=True))
    op.add_column("processed_data", sa.Column("resolution", enum("flag_resolution"), nullable=True))
    op.add_column("processed_data", sa.Column("dismiss_reason", enum("flag_dismiss_reason"), nullable=True))
    op.add_column("processed_data", sa.Column("resolution_note", sa.Text(), nullable=True))
    op.create_foreign_key("fk_processed_data_reviewed_by_users", "processed_data", "users", ["reviewed_by"], ["id"])

    op.create_table(
        "scheduled_visits",
        sa.Column("id", UUID, nullable=False),
        sa.Column("worker_id", UUID, nullable=False),
        sa.Column("citizen_id", UUID, nullable=False),
        sa.Column("case_id", UUID, nullable=True),
        sa.Column("scheduled_for", TZ, nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("status", enum("visit_status"), server_default=sa.text("'scheduled'"), nullable=False),
        sa.Column("location", sa.String(160), nullable=True),
        sa.Column("created_at", TZ, nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_scheduled_visits"),
        sa.ForeignKeyConstraint(
            ["worker_id"], ["users.id"], name="fk_scheduled_visits_worker_id_users", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["citizen_id"], ["users.id"], name="fk_scheduled_visits_citizen_id_users", ondelete="CASCADE"
        ),
        # SET NULL: losing the flag must not cancel the visit.
        sa.ForeignKeyConstraint(
            ["case_id"], ["processed_data.id"], name="fk_scheduled_visits_case_id_processed_data", ondelete="SET NULL"
        ),
    )
    op.create_index("ix_scheduled_visits_worker_id", "scheduled_visits", ["worker_id"])
    op.create_index("ix_scheduled_visits_citizen_id", "scheduled_visits", ["citizen_id"])
    op.create_index("ix_scheduled_visits_worker_id_scheduled_for", "scheduled_visits", ["worker_id", "scheduled_for"])


def downgrade() -> None:
    op.drop_table("scheduled_visits")
    op.drop_constraint("fk_processed_data_reviewed_by_users", "processed_data", type_="foreignkey")
    for column in ("resolution_note", "dismiss_reason", "resolution", "reviewed_by", "reviewed_at"):
        op.drop_column("processed_data", column)
