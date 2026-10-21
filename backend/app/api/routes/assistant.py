"""The AI health assistant: chat sessions and questions, for citizens, PHC workers and admins.

Each person only ever sees their own sessions; answers are drawn from their own
scope (services/assistant). A session that is not yours is "not found".
"""

import uuid
from datetime import datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, StringConstraints
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.dependencies import require_any_verified
from app.db.session import get_session
from app.models import ChatMessage, ChatSession, User
from app.models.base import utcnow
from app.models.enums import ChatMessageRole, ChatRefusalReason
from app.services import assistant
from app.services.assistant import llm

router = APIRouter(prefix="/assistant", tags=["assistant"])

SESSION_NOT_FOUND = "Conversation not found."

Question = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]
Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    role: ChatMessageRole
    content: str
    created_at: datetime
    was_refused: bool
    refusal_reason: ChatRefusalReason | None
    retrieval: dict[str, Any] | None
    latency_ms: int | None


class SessionDetail(SessionOut):
    messages: list[MessageOut]


class AskIn(BaseModel):
    content: Question
    # None starts a new conversation.
    session_id: uuid.UUID | None = None


class AskOut(BaseModel):
    session: SessionOut
    question: MessageOut
    answer: MessageOut


class Info(BaseModel):
    suggestions: list[str]
    engine: str
    model: str | None


class Rename(BaseModel):
    title: Title


async def _own_session(db: AsyncSession, user: User, session_id: uuid.UUID) -> ChatSession:
    session = await db.scalar(select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user.id))
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, SESSION_NOT_FOUND)
    return session


@router.get("/info", response_model=Info)
async def info(user: User = Depends(require_any_verified)) -> Info:
    on = llm.enabled()
    return Info(
        suggestions=assistant.suggestions_for(user.role),
        engine="gemini" if on else "rules",
        model=get_settings().GEMINI_MODEL if on else None,
    )


@router.get("/sessions", response_model=list[SessionOut])
async def list_sessions(
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(require_any_verified),
    db: AsyncSession = Depends(get_session),
) -> list[ChatSession]:
    rows = await db.scalars(
        select(ChatSession).where(ChatSession.user_id == user.id).order_by(ChatSession.updated_at.desc()).limit(limit)
    )
    return list(rows.all())


@router.get("/sessions/{session_id}", response_model=SessionDetail)
async def get_session_detail(
    session_id: uuid.UUID, user: User = Depends(require_any_verified), db: AsyncSession = Depends(get_session)
) -> SessionDetail:
    session = await _own_session(db, user, session_id)
    messages = (
        await db.scalars(
            select(ChatMessage).where(ChatMessage.session_id == session.id).order_by(ChatMessage.created_at)
        )
    ).all()
    return SessionDetail(
        **SessionOut.model_validate(session).model_dump(),
        messages=[MessageOut.model_validate(m) for m in messages],
    )


@router.patch("/sessions/{session_id}", response_model=SessionOut)
async def rename_session(
    session_id: uuid.UUID,
    data: Rename,
    user: User = Depends(require_any_verified),
    db: AsyncSession = Depends(get_session),
) -> ChatSession:
    session = await _own_session(db, user, session_id)
    session.title = data.title
    session.auto_titled = False
    await db.commit()
    await db.refresh(session)
    return session


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: uuid.UUID, user: User = Depends(require_any_verified), db: AsyncSession = Depends(get_session)
) -> None:
    session = await _own_session(db, user, session_id)
    await db.delete(session)
    await db.commit()


@router.delete("/sessions", status_code=status.HTTP_204_NO_CONTENT)
async def delete_all_sessions(user: User = Depends(require_any_verified), db: AsyncSession = Depends(get_session)) -> None:
    await db.execute(delete(ChatSession).where(ChatSession.user_id == user.id))
    await db.commit()


@router.post("/ask", response_model=AskOut)
async def ask(
    data: AskIn, user: User = Depends(require_any_verified), db: AsyncSession = Depends(get_session)
) -> AskOut:
    limit = get_settings().ASSISTANT_QUESTIONS_PER_MINUTE
    recent = await db.scalar(
        select(func.count()).where(
            ChatMessage.user_id == user.id,
            ChatMessage.role == ChatMessageRole.user,
            ChatMessage.created_at >= utcnow() - timedelta(minutes=1),
        )
    )
    if (recent or 0) >= limit:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "You are asking very quickly. Please wait 60 seconds and try again.",
            headers={"Retry-After": "60"},
        )

    if data.session_id is None:
        session = ChatSession(user_id=user.id)
        db.add(session)
        await db.flush()
    else:
        session = await _own_session(db, user, data.session_id)

    question, answer = await assistant.ask(db, user, session, data.content)
    await db.refresh(session)
    return AskOut(
        session=SessionOut.model_validate(session),
        question=MessageOut.model_validate(question),
        answer=MessageOut.model_validate(answer),
    )
