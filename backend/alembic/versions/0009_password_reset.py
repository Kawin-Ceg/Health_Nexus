"""users password-reset columns + index

Separate from the verification columns on purpose: a reset must never consume
a pending address verification.

Revision ID: 0009
Revises: 0008
Create Date: 2026-09-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TZ = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.add_column("users", sa.Column("password_reset_token_hash", sa.String(), nullable=True))
    op.add_column("users", sa.Column("password_reset_expires_at", TZ, nullable=True))
    op.add_column("users", sa.Column("password_reset_sent_at", TZ, nullable=True))
    op.create_index("ix_users_password_reset_token_hash", "users", ["password_reset_token_hash"])


def downgrade() -> None:
    op.drop_index("ix_users_password_reset_token_hash", table_name="users")
    for column in ("password_reset_sent_at", "password_reset_expires_at", "password_reset_token_hash"):
        op.drop_column("users", column)
