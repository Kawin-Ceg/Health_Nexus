"""advisories: target one locality, or a health centre plus people living near it

Revision ID: 0017
Revises: 0016
Create Date: 2026-10-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE advisory_scope ADD VALUE IF NOT EXISTS 'area'")
    op.add_column("advisories", sa.Column("area", sa.String(120), nullable=True))
    op.add_column("advisories", sa.Column("radius_km", sa.Float(), nullable=True))
    op.add_column("advisories", sa.Column("centre_lat", sa.Float(), nullable=True))
    op.add_column("advisories", sa.Column("centre_lng", sa.Float(), nullable=True))


def downgrade() -> None:
    for column in ("centre_lng", "centre_lat", "radius_km", "area"):
        op.drop_column("advisories", column)
