"""valid_phc_facilities + users.phc_id / district / state / pincode / area / geo

users.phc_id is the catchment link: a worker sees citizens with the same phc_id.

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)
TZ = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "valid_phc_facilities",
        sa.Column("id", UUID, nullable=False),
        sa.Column("facility_code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("normalised_name", sa.String(), nullable=False),
        sa.Column("district", sa.String(), nullable=False),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("block", sa.String(), nullable=True),
        sa.Column("official_email_domain", sa.String(), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("is_placeholder", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", TZ, nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_valid_phc_facilities"),
    )
    op.create_index("ix_valid_phc_facilities_facility_code", "valid_phc_facilities", ["facility_code"], unique=True)
    op.create_index("ix_valid_phc_facilities_normalised_name", "valid_phc_facilities", ["normalised_name"])
    op.create_index("ix_valid_phc_facilities_district", "valid_phc_facilities", ["district"])
    op.create_index("ix_valid_phc_facilities_state", "valid_phc_facilities", ["state"])

    op.add_column("users", sa.Column("phc_id", UUID, nullable=True))
    op.add_column("users", sa.Column("district", sa.String(), nullable=True))
    op.add_column("users", sa.Column("state", sa.String(), nullable=True))
    op.add_column("users", sa.Column("pincode", sa.String(6), nullable=True))
    op.add_column("users", sa.Column("area", sa.String(120), nullable=True))
    op.add_column("users", sa.Column("geo_lat", sa.Float(), nullable=True))
    op.add_column("users", sa.Column("geo_lng", sa.Float(), nullable=True))
    op.create_foreign_key(
        "fk_users_phc_id_valid_phc_facilities", "users", "valid_phc_facilities", ["phc_id"], ["id"]
    )
    op.create_index("ix_users_phc_id", "users", ["phc_id"])
    op.create_index("ix_users_district", "users", ["district"])
    op.create_index("ix_users_state", "users", ["state"])
    op.create_index("ix_users_pincode", "users", ["pincode"])


def downgrade() -> None:
    op.drop_index("ix_users_pincode", table_name="users")
    op.drop_index("ix_users_state", table_name="users")
    op.drop_index("ix_users_district", table_name="users")
    op.drop_index("ix_users_phc_id", table_name="users")
    op.drop_constraint("fk_users_phc_id_valid_phc_facilities", "users", type_="foreignkey")
    for column in ("geo_lng", "geo_lat", "area", "pincode", "state", "district", "phc_id"):
        op.drop_column("users", column)
    op.drop_table("valid_phc_facilities")
