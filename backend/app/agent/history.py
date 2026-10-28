"""Portal-owned durable Agent conversation and run state.

Only completed business answers and allowlisted tool metadata are persisted.
Gateway remains the sole owner of Harness execution; Portal owns history and identity.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from datetime import datetime
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.db.application_models import AgentConversation, AgentToolEvent, AgentTurn
from backend.app.db.session import SessionLocal

ACTIVE = ("queued", "running", "cancel_requested")
TERMINAL = ("completed", "failed", "cancelled", "timeout", "interrupted")
TOOL_NAMES = frozenset(json.loads(
    (Path(__file__).resolve().parents[3] / "agent" / "tool-catalog.json").read_text(encoding="utf-8")
)["tools"])


def _json(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _decode(raw, fallback):
    if not raw:
        return fallback
    try:
        value = json.loads(raw)
        return value if isinstance(value, type(fallback)) else fallback
    except (ValueError, TypeError):
        return fallback


def owned(db: Session, user_id: int, conversation_id: str) -> AgentConversation:
    conv = db.get(AgentConversation, conversation_id)
    if conv is None or conv.user_id != user_id:
        raise HTTPException(404, "Agent conversation not found")
    return conv


def create(db: Session, user_id: int, title: str, mode: str, *,
           legacy_messages=None, session_id=None, pinned=False, context_asset=None,
           task_tier="standard") -> AgentConversation:
    conv = AgentConversation(
        id=str(uuid4()), user_id=user_id, title=title[:200] or "新会话",
        model_mode=mode, task_tier=task_tier, pinned=pinned, session_id=session_id,
        legacy_messages_json=_json(legacy_messages[:80]) if legacy_messages is not None else None,
        context_asset_json=_json(context_asset) if context_asset else None,
        created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
    )
    db.add(conv)
    db.commit()
    return conv


def _safe_answer(result: dict) -> dict:
    # Exclude raw tool inputs, model thinking, and unexpected provider payloads.
    permitted = (
        "sessionId", "answer", "summary", "stopReason", "sql", "validation",
        "validationState", "sqlSourceCallId", "validationCallId",
        "clarification", "researchPolicy", "semanticPlan",
        "semanticValidation", "evidence", "sqlExecuted", "hiddenReasoningExposed",
        "durationMs", "toolCallCount",
    )
    clean = {key: result[key] for key in permitted if key in result}
    clean["sqlExecuted"] = False
    clean["hiddenReasoningExposed"] = False
    clean["events"] = [
        {"type": e["type"], "tool": e["tool"], "callId": e.get("callId"),
         **({"status": e.get("status")} if e["type"] == "tool_result" else {})}
        for e in result.get("events", []) if isinstance(e, dict)
        and e.get("type") in ("tool_call", "tool_result")
        and e.get("tool") in TOOL_NAMES
    ][:120]
    return clean


def serialize(db: Session, conv: AgentConversation) -> dict:
    messages = _decode(conv.legacy_messages_json, [])[:80]
    turns = db.execute(
        select(AgentTurn).where(AgentTurn.conversation_id == conv.id)
        .order_by(AgentTurn.created_at, AgentTurn.id)
    ).scalars().all()
    for turn in turns:
        messages.append({"role": "user", "text": turn.display_question or turn.question})
        if turn.status == "completed":
            result = _decode(turn.result_json, {})
            messages.append({
                "role": "assistant", "text": result.get("answer") or "分析完成。",
                **{k: result[k] for k in ("summary", "sql", "validation", "validationState",
                    "evidence", "events", "clarification", "durationMs", "toolCallCount") if k in result},
            })
        elif turn.status in TERMINAL:
            messages.append({
                "role": "assistant",
                "text": "本轮任务已结束（" + turn.status + "），没有可采信的最终结果。",
            })
    return {
        "id": conv.id, "serverId": conv.id, "title": conv.title,
        "modelMode": conv.model_mode, "taskTier": conv.task_tier,
        "sessionId": conv.session_id,
        "pinned": conv.pinned, "messages": messages[-80:],
        "contextAsset": _decode(conv.context_asset_json, {}) if conv.context_asset_json else None,
        "createdAt": int(conv.created_at.timestamp() * 1000),
        "updatedAt": int(conv.updated_at.timestamp() * 1000),
        "lastRunStatus": turns[-1].status if turns else None,
    }


def reserve(db: Session, user_id: int, conversation_id: str, run_id: str,
            question: str, mode: str, display_question: str | None = None) -> tuple[AgentTurn, bool]:
    conv = owned(db, user_id, conversation_id)
    if conv.model_mode != mode:
        raise HTTPException(409, "Cannot resume conversation with another model")
    previous = db.get(AgentTurn, run_id)
    if previous is not None:
        if previous.conversation_id != conv.id or previous.question != question or previous.model_mode != mode:
            raise HTTPException(409, "runId is already assigned to a different request")
        if previous.status in ACTIVE:
            raise HTTPException(409, "Agent run is already active")
        return previous, True
    if db.execute(select(AgentTurn.id).where(
        AgentTurn.conversation_id == conv.id, AgentTurn.status.in_(ACTIVE)
    ).limit(1)).first():
        raise HTTPException(409, "Conversation already has an active run")
    if db.execute(select(AgentTurn.id).join(AgentConversation).where(
        AgentConversation.user_id == user_id, AgentTurn.status.in_(ACTIVE)
    ).limit(2)).all().__len__() >= 2:
        raise HTTPException(429, "User has reached the concurrent run limit")
    turn = AgentTurn(
        id=run_id, conversation_id=conversation_id, model_mode=mode,
        question=question, display_question=display_question or question,
        status="queued", created_at=datetime.utcnow()
    )
    db.add(turn)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Concurrent Agent run or duplicate runId") from exc
    return turn, False


def transition(run_id: str, status: str, *, result=None, error=None):
    if status not in (*ACTIVE, *TERMINAL):
        raise ValueError("Unknown Agent status")
    with SessionLocal() as db:
        turn = db.get(AgentTurn, run_id)
        if not turn or turn.status in TERMINAL:
            return
        # Never overwrite a cancellation intent with a delayed 'running' signal.
        if turn.status == "cancel_requested" and status == "running":
            return
        turn.status = status
        if status in TERMINAL:
            turn.finished_at = datetime.utcnow()
            if result is not None and status == "completed":
                if result.get("sqlExecuted") is True or result.get("hiddenReasoningExposed") is True:
                    turn.status = "failed"
                    error = "Agent result violated execution or reasoning policy"
                else:
                    safe = _safe_answer(result)
                    turn.result_json = _json(safe)
                    conv = db.get(AgentConversation, turn.conversation_id)
                    if conv:
                        conv.session_id = safe.get("sessionId")
                        conv.updated_at = datetime.utcnow()
            if turn.status != "completed":
                conv = db.get(AgentConversation, turn.conversation_id)
                if conv:
                    conv.session_id = None
                    conv.updated_at = datetime.utcnow()
            turn.error = str(error)[:240] if error else None
        db.commit()


def append_activity(run_id: str, activity: dict):
    e = activity.get("event") if activity.get("type") == "activity" else None
    if not isinstance(e, dict) or e.get("type") not in ("tool_call", "tool_result"):
        return
    if e.get("tool") not in TOOL_NAMES:
        return
    call_id = e.get("callId")
    if not isinstance(call_id, str) or not re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", call_id):
        return
    status = e.get("status")
    if status not in (None, "completed", "error", "failed", "success", "unknown"):
        status = "unknown"
    with SessionLocal() as db:
        turn = db.get(AgentTurn, run_id)
        if not turn or turn.status in TERMINAL:
            return
        sequence = db.query(AgentToolEvent).filter_by(turn_id=run_id).count() + 1
        if sequence > 120:
            return
        db.add(AgentToolEvent(
            turn_id=run_id, sequence=sequence, event_type=e["type"],
            call_id=call_id, tool=e["tool"], status=status,
            created_at=datetime.utcnow(),
        ))
        db.commit()


def reconcile_startup():
    """Portal restarts cannot truthfully claim an in-memory Gateway run finished."""
    from sqlalchemy import inspect
    from backend.app.db.session import engine
    if not inspect(engine).has_table(AgentTurn.__tablename__):
        return
    with SessionLocal() as db:
        turns = db.execute(select(AgentTurn).where(AgentTurn.status.in_(ACTIVE))).scalars().all()
        for turn in turns:
            turn.status = "interrupted"
            turn.error = "Portal restarted before observing a terminal event"
            turn.finished_at = datetime.utcnow()
            conv = db.get(AgentConversation, turn.conversation_id)
            if conv:
                conv.session_id = None
                conv.updated_at = datetime.utcnow()
        db.commit()
