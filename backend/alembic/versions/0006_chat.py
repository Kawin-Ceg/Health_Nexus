"""chat_sessions, chat_messages

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)
TZ = sa.DateTime(timezone=True)


def enum(name: str) -> postgresql.ENUM:
    return postgresql.ENUM(name=name, create_type=False)


def upgrade() -> None:
    op.create_table(
        "chat_sessions",
        sa.Column("id", UUID, nullable=False),
        sa.Column("user_id", UUID, nullable=False),
        sa.Column("title", sa.String(120), server_default=sa.text("'New chat'"), nullable=False),
        sa.Column("auto_titled", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", TZ, nullable=False),
        sa.Column("updated_at", TZ, nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_chat_sessions"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_chat_sessions_user_id_users", ondelete="CASCADE"),
    )
    op.create_index("ix_chat_sessions_user_id", "chat_sessions", ["user_id"])
    op.create_index("ix_chat_sessions_user_id_updated_at", "chat_sessions", ["user_id", "updated_at"])

    op.create_table(
        "chat_messages",
        sa.Column("id", UUID, nullable=False),
        sa.Column("session_id", UUID, nullable=False),
        sa.Column("user_id", UUID, nullable=False),
        sa.Column("role", enum("chat_message_role"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("generated_sql", sa.Text(), nullable=True),
        sa.Column("retrieval", postgresql.JSONB(), nullable=True),
        sa.Column("was_refused", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("refusal_reason", enum("chat_refusal_reason"), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("created_at", TZ, nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_chat_messages"),
        sa.ForeignKeyConstraint(
            ["session_id"], ["chat_sessions.id"], name="fk_chat_messages_session_id_chat_sessions", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_chat_messages_user_id_users", ondelete="CASCADE"),
    )
    op.create_index("ix_chat_messages_session_id", "chat_messages", ["session_id"])
    op.create_index("ix_chat_messages_user_id", "chat_messages", ["user_id"])
    op.create_index("ix_chat_messages_session_id_created_at", "chat_messages", ["session_id", "created_at"])


def downgrade() -> None:
    op.drop_table("chat_messages")
    op.drop_table("chat_sessions")
