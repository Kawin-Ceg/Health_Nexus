"""processed_data: how each reading was judged (basis, model version, per-vital details)

Nullable on purpose: rows scored by the placeholder before this migration have
none of these, and the pages treat a missing value as "published ranges".

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("processed_data", sa.Column("basis", sa.String(32), nullable=True))
    op.add_column("processed_data", sa.Column("model_version", sa.String(64), nullable=True))
    op.add_column("processed_data", sa.Column("details", sa.JSON(), nullable=True))


def downgrade() -> None:
    for column in ("details", "model_version", "basis"):
        op.drop_column("processed_data", column)
