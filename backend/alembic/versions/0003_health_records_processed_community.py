"""health_records, processed_data, community_data

processed_data starts with the scoring columns only; the review/resolution
columns arrive in 0007.

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)
TZ = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "health_records",
        sa.Column("id", UUID, nullable=False),
        sa.Column("user_id", UUID, nullable=False),
        sa.Column("vitals", sa.JSON(), nullable=False),
        sa.Column("symptoms", sa.JSON(), nullable=False),
        sa.Column("geo_lat", sa.Float(), nullable=True),
        sa.Column("geo_lng", sa.Float(), nullable=True),
        sa.Column("timestamp", TZ, nullable=False),
        sa.Column("created_at", TZ, nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_health_records"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_health_records_user_id_users"),
    )
    op.create_index("ix_health_records_user_id", "health_records", ["user_id"])

    op.create_table(
        "processed_data",
        sa.Column("id", UUID, nullable=False),
        sa.Column("health_record_id", UUID, nullable=False),
        sa.Column("user_id", UUID, nullable=False),
        sa.Column("features", sa.JSON(), nullable=False),
        sa.Column("anomaly_score", sa.Float(), nullable=False),
        sa.Column("is_anomaly", sa.Boolean(), nullable=False),
        sa.Column("processed_at", TZ, nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_processed_data"),
        sa.ForeignKeyConstraint(
            ["health_record_id"], ["health_records.id"], name="fk_processed_data_health_record_id_health_records"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_processed_data_user_id_users"),
        sa.UniqueConstraint("health_record_id", name="uq_processed_data_health_record_id"),
    )
    op.create_index("ix_processed_data_user_id", "processed_data", ["user_id"])

    op.create_table(
        "community_data",
        sa.Column("id", UUID, nullable=False),
        sa.Column("region", sa.String(), nullable=False),
        sa.Column("symptom_cluster", sa.JSON(), nullable=False),
        sa.Column("prevalence_score", sa.Float(), nullable=False),
        sa.Column("outbreak_flag", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("window_start", TZ, nullable=False),
        sa.Column("window_end", TZ, nullable=False),
        sa.Column("created_at", TZ, nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_community_data"),
    )
    op.create_index("ix_community_data_region", "community_data", ["region"])


def downgrade() -> None:
    op.drop_table("community_data")
    op.drop_table("processed_data")
    op.drop_table("health_records")
