"""community_data: one row per outbreak cluster found by a clustering run; advisories may cite one

Revision ID: 0014
Revises: 0013
Create Date: 2026-10-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)
TZ = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.execute("DELETE FROM community_data")
    for column in (
        sa.Column("syndrome", sa.String(32), nullable=False),
        sa.Column("cases", sa.Integer(), nullable=False),
        sa.Column("expected", sa.Float(), nullable=False),
        sa.Column("p_value", sa.Float(), nullable=False),
        sa.Column("centre_lat", sa.Float(), nullable=False),
        sa.Column("centre_lng", sa.Float(), nullable=False),
        sa.Column("radius_km", sa.Float(), nullable=False),
        sa.Column("district", sa.String(), nullable=True),
        sa.Column("phc_ids", sa.JSON(), nullable=False),
        sa.Column("first_onset", TZ, nullable=False),
        sa.Column("last_onset", TZ, nullable=False),
        sa.Column("acknowledged_at", TZ, nullable=True),
        sa.Column("acknowledged_by", UUID, nullable=True),
    ):
        op.add_column("community_data", column)
    op.create_foreign_key(
        "fk_community_data_acknowledged_by_users", "community_data", "users", ["acknowledged_by"], ["id"], ondelete="SET NULL"
    )
    op.create_index("ix_community_data_window_end", "community_data", ["window_end"])
    op.add_column("advisories", sa.Column("cluster_id", UUID, nullable=True))
    op.create_foreign_key(
        "fk_advisories_cluster_id_community_data", "advisories", "community_data", ["cluster_id"], ["id"], ondelete="SET NULL"
    )


def downgrade() -> None:
    op.drop_constraint("fk_advisories_cluster_id_community_data", "advisories", type_="foreignkey")
    op.drop_column("advisories", "cluster_id")
    op.drop_index("ix_community_data_window_end", "community_data")
    op.drop_constraint("fk_community_data_acknowledged_by_users", "community_data", type_="foreignkey")
    for column in (
        "acknowledged_by", "acknowledged_at", "last_onset", "first_onset", "phc_ids", "district",
        "radius_km", "centre_lng", "centre_lat", "p_value", "expected", "cases", "syndrome",
    ):
        op.drop_column("community_data", column)
