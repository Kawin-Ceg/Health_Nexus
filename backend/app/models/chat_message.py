import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Index, Text, false
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, CreatedAt, UUIDPk
from .enums import ChatMessageRole, ChatRefusalReason, pg_enum

if TYPE_CHECKING:
    from .chat_session import ChatSession


class ChatMessage(UUIDPk, CreatedAt, Base):
    __tablename__ = "chat_messages"
    __table_args__ = (Index("ix_chat_messages_session_id_created_at", "session_id", "created_at"),)

    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chat_sessions.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[ChatMessageRole] = mapped_column(pg_enum(ChatMessageRole, "chat_message_role"))
    content: Mapped[str] = mapped_column(Text)
    generated_sql: Mapped[str | None] = mapped_column(Text)
    retrieval: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    was_refused: Mapped[bool] = mapped_column(default=False, server_default=false())
    refusal_reason: Mapped[ChatRefusalReason | None] = mapped_column(pg_enum(ChatRefusalReason, "chat_refusal_reason"))
    latency_ms: Mapped[int | None]
    tokens_used: Mapped[int | None]

    session: Mapped["ChatSession"] = relationship(back_populates="messages")
