"""Authenticated server history. Anonymous Agent queries retain local-only history."""
from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from backend.app.agent import history
from backend.app.api.auth import get_current_user
from backend.app.db.application_models import AgentConversation, AgentToolEvent, AgentTurn
from backend.app.db.models import User
from backend.app.db.session import SessionLocal

router = APIRouter(prefix="/api/v1/agent/conversations", tags=["agent-history"])


class ConversationNew(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    modelMode: Literal["deepseek"] = "deepseek"
    taskTier: Literal["standard", "multi"] = "standard"
    contextAsset: dict[str, Any] | None = None


class ConversationEdit(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    pinned: bool | None = None


class LegacyConversation(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    modelMode: Literal["deepseek", "free-test"] = "deepseek"
    pinned: bool = False
    taskTier: Literal["standard", "multi"] = "standard"
    sessionId: str | None = Field(default=None, max_length=200)
    messages: list[dict[str, Any]] = Field(default_factory=list, max_length=80)
    contextAsset: dict[str, Any] | None = None


class ImportRequest(BaseModel):
    conversations: list[LegacyConversation] = Field(max_length=40)


@router.get("")
def list_conversations(user: User = Depends(get_current_user)):
    with SessionLocal() as db:
        rows = db.execute(select(AgentConversation).where(AgentConversation.user_id == user.id)
                          .order_by(AgentConversation.updated_at.desc()).limit(80)).scalars().all()
        return {"code": "OK", "data": [history.serialize(db, row) for row in rows]}


@router.post("")
def new_conversation(body: ConversationNew, user: User = Depends(get_current_user)):
    with SessionLocal() as db:
        return {"code": "OK", "data": history.serialize(db, history.create(
            db, user.id, body.title.strip(), body.modelMode,
            context_asset=body.contextAsset, task_tier=body.taskTier,
        ))}


@router.post("/import")
def import_legacy(body: ImportRequest, user: User = Depends(get_current_user)):
    # Invoked only after an explicit confirmation in the browser.
    imported = []
    with SessionLocal() as db:
        for item in body.conversations:
            if not item.messages:
                continue
            rows = [{k: m[k] for k in (
                "role", "text", "summary", "sql", "validation", "validationState", "evidence",
                "events", "clarification", "clarificationResolved", "clarificationSelection"
            ) if k in m} for m in item.messages[:80] if m.get("role") in ("user", "assistant")
                and isinstance(m.get("text"), str)]
            for m in rows:
                m.pop("events", None)  # legacy events may contain raw tool inputs
            mode = item.modelMode
            session = item.sessionId
            if session and ((mode == "free-test") != session.startswith("free-test:")):
                session = None
            conv = history.create(
                db, user.id, item.title, mode, legacy_messages=rows,
                session_id=None, pinned=item.pinned, context_asset=item.contextAsset,
                task_tier=item.taskTier if mode == "deepseek" else "standard",
            )
            imported.append(history.serialize(db, conv))
    return {"code": "OK", "data": imported}


@router.get("/{conversation_id}")
def get_conversation(conversation_id: UUID, user: User = Depends(get_current_user)):
    with SessionLocal() as db:
        return {"code": "OK", "data": history.serialize(db, history.owned(db, user.id, str(conversation_id)))}


@router.patch("/{conversation_id}")
def edit_conversation(conversation_id: UUID, body: ConversationEdit,
                      user: User = Depends(get_current_user)):
    with SessionLocal() as db:
        conv = history.owned(db, user.id, str(conversation_id))
        if body.title is not None:
            conv.title = body.title.strip() or conv.title
        if body.pinned is not None:
            conv.pinned = body.pinned
        from datetime import datetime
        conv.updated_at = datetime.utcnow()
        db.commit()
        return {"code": "OK", "data": history.serialize(db, conv)}


@router.delete("/{conversation_id}")
def delete_conversation(conversation_id: UUID, user: User = Depends(get_current_user)):
    with SessionLocal() as db:
        conv = history.owned(db, user.id, str(conversation_id))
        if db.execute(select(AgentTurn.id).where(
            AgentTurn.conversation_id == conv.id, AgentTurn.status.in_(history.ACTIVE)
        ).limit(1)).first():
            raise HTTPException(409, "Stop the active run before deleting this conversation")
        turns = db.execute(select(AgentTurn.id).where(
            AgentTurn.conversation_id == conv.id
        )).scalars().all()
        if turns:
            db.query(AgentToolEvent).filter(AgentToolEvent.turn_id.in_(turns)).delete(synchronize_session=False)
            db.query(AgentTurn).filter(AgentTurn.id.in_(turns)).delete(synchronize_session=False)
        db.delete(conv)
        db.commit()
        return {"code": "OK", "data": {"deleted": True}}
