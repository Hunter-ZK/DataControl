"""R1-B tests: owner isolation, run lifecycle, replay and sanitized evidence."""
from __future__ import annotations

import json
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.agent import history
from backend.app.db.application_models import AgentToolEvent, AgentTurn
from backend.app.db.models import Base, User


@pytest.fixture
def store(monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(history, "SessionLocal", factory)
    with factory() as db:
        db.add_all([
            User(id=1, username="test-1", display_name="User One"),
            User(id=2, username="test-2", display_name="User Two"),
        ])
        db.commit()
        yield db
    engine.dispose()


def test_history_owner_and_model_isolation(store):
    conv = history.create(store, 1, "指标问答", "deepseek")
    assert history.owned(store, 1, conv.id).id == conv.id
    with pytest.raises(HTTPException) as exc:
        history.owned(store, 2, conv.id)
    assert exc.value.status_code == 404
    with pytest.raises(HTTPException) as exc:
        history.reserve(store, 1, conv.id, str(uuid4()), "synthetic question", "free-test")
    assert exc.value.status_code == 409


def test_run_idempotency_and_one_active_turn(store):
    conv = history.create(store, 1, "测试会话", "deepseek")
    run_id = str(uuid4())
    turn, replay = history.reserve(store, 1, conv.id, run_id, "question one", "deepseek")
    assert replay is False and turn.status == "queued"
    with pytest.raises(HTTPException) as exc:
        history.reserve(store, 1, conv.id, run_id, "question one", "deepseek")
    assert exc.value.status_code == 409
    with pytest.raises(HTTPException) as exc:
        history.reserve(store, 1, conv.id, str(uuid4()), "question two", "deepseek")
    assert exc.value.status_code == 409
    history.transition(run_id, "completed", result={
        "answer": "已验证", "sessionId": "session-test", "sqlExecuted": False,
        "hiddenReasoningExposed": False,
    })
    repeated, replay = history.reserve(store, 1, conv.id, run_id, "question one", "deepseek")
    assert replay is True and repeated.status == "completed"
    with pytest.raises(HTTPException):
        history.reserve(store, 1, conv.id, run_id, "different question", "deepseek")
    assert history.serialize(store, conv)["sessionId"] == "session-test"


def test_result_and_events_never_persist_raw_tool_input(store):
    conv = history.create(store, 1, "脱敏测试", "deepseek")
    run_id = str(uuid4())
    history.reserve(store, 1, conv.id, run_id, "synthetic question", "deepseek")
    secret = "dont-log-raw-tool-input"
    history.append_activity(run_id, {
        "type": "activity",
        "event": {"type": "tool_call", "callId": "tool-1", "tool": "resolve_metric",
                  "input": {"credential": secret}},
    })
    history.append_activity(run_id, {
        "type": "activity",
        "event": {"type": "thinking", "text": secret},
    })
    history.transition(run_id, "completed", result={
        "answer": "可信结论", "events": [
            {"type": "tool_call", "tool": "resolve_metric", "callId": "tool-1",
             "input": {"credential": secret}},
        ], "rawProviderPayload": secret, "sqlExecuted": False,
        "hiddenReasoningExposed": False,
    })
    saved = store.get(AgentTurn, run_id)
    assert secret not in saved.result_json
    assert "rawProviderPayload" not in saved.result_json
    assert len(store.execute(select(AgentToolEvent)).scalars().all()) == 1
    assert history.serialize(store, conv)["messages"][-1]["text"] == "可信结论"


def test_failed_or_cancelled_run_must_invalidate_session(store):
    conv = history.create(store, 1, "失败重试", "deepseek", session_id="prior-good")
    run_id = str(uuid4())
    history.reserve(store, 1, conv.id, run_id, "question", "deepseek")
    history.transition(run_id, "cancel_requested")
    history.transition(run_id, "running")  # delayed startup cannot override stop
    assert store.get(AgentTurn, run_id).status == "cancel_requested"
    history.transition(run_id, "cancelled")
    assert history.serialize(store, conv)["sessionId"] is None
    history.transition(run_id, "completed", result={"answer": "late result"})
    assert store.get(AgentTurn, run_id).status == "cancelled"


def test_displayed_question_differs_from_internal_prompt(store):
    conv = history.create(store, 1, "字段查询", "deepseek")
    run_id = str(uuid4())
    history.reserve(store, 1, conv.id, run_id, "internal asset context + question",
                    "deepseek", display_question="字段是什么意思？")
    history.transition(run_id, "failed")
    assert history.serialize(store, conv)["messages"][-2]["text"] == "字段是什么意思？"


def test_bounded_legacy_history_is_preserved(store):
    original = [{"role": "user", "text": "旧问题"}, {"role": "assistant", "text": "旧答案"}]
    conv = history.create(store, 1, "旧会话", "free-test", legacy_messages=original,
                          session_id="free-test:safe-id")
    serialized = history.serialize(store, conv)
    assert serialized["modelMode"] == "free-test"
    assert serialized["messages"] == original
    assert serialized["sessionId"] == "free-test:safe-id"
