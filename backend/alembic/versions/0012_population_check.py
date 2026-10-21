"""processed_data.population: the trained population model's check of each reading

{"score", "percentile", "features", "version"} from services/population.py.
NULL for readings scored before this migration, without heart rate or breathing
rate, or while the model was not loaded.

Revision ID: 0012
Revises: 0011
Create Date: 2026-10-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("processed_data", sa.Column("population", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("processed_data", "population")
