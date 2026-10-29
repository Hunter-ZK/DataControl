from __future__ import annotations

from dataclasses import asdict
import json
import logging
from uuid import UUID
from typing import Literal

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.app.agent.runtime import AgentRuntimeError, EmbeddedAgentGateway
from backend.app.agent import history
from backend.app.api.auth import get_current_user, get_optional_user
from backend.app.db.models import User
from backend.app.db.application_models import AgentTurn
from backend.app.db.session import SessionLocal

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])


class AgentQuery(BaseModel):
    question: str = Field(min_length=2, max_length=4000)
    sessionId: str | None = Field(default=None, max_length=200)
    runId: UUID | None = None
    conversationId: UUID | None = None
    displayQuestion: str | None = Field(default=None, max_length=4000)
    modelMode: Literal["deepseek", "free-test"] = "deepseek"
    taskTier: Literal["standard", "multi"] = "standard"
    publicGatewayConsent: bool = False


def check_public_test(mode: str, consent: bool = False) -> None:
    if mode != "free-test":
        return
    if not consent:
        raise HTTPException(403, "Public model request requires the client's explicit consent")


@router.get("/status")
async def agent_status(modelMode: Literal["deepseek", "free-test"] = "deepseek",
                       taskTier: Literal["standard", "multi"] = "standard"):
    status = await EmbeddedAgentGateway().status(modelMode, taskTier)
    return {
        "code": "OK",
        "data": {
            **asdict(status),
            "sqlExecutionEnabled": False,
            "hiddenReasoningExposed": False,
        },
    }


@router.post("/query")
async def agent_query(body: AgentQuery, user: User = Depends(get_current_user)):
    # Legacy one-shot API: authenticated and deliberately stateless.
    # A caller-controlled dsh session could otherwise cross user boundaries.
    if body.sessionId or body.conversationId:
        raise HTTPException(400, detail="Use authenticated conversation stream for continuation")
    check_public_test(body.modelMode, body.publicGatewayConsent)
    runtime = EmbeddedAgentGateway()
    status = await runtime.status(body.modelMode, body.taskTier)
    if not status.ready:
        raise HTTPException(
            503,
            detail={
                "message": "Intelligent Q&A runtime is not ready",
                "reason": status.reason,
                "mode": status.mode,
                "source": status.source,
                "sessionBridgeImplemented": status.sessionBridgeImplemented,
                "integrated": status.integrated,
                "serviceReachable": status.serviceReachable,
            },
        )
    try:
        data = await runtime.run(
            body.question.strip(), session_id=body.sessionId,
            model_mode=body.modelMode, public_gateway_consent=body.publicGatewayConsent,
            task_tier=body.taskTier,
        )
    except AgentRuntimeError as exc:
        raise HTTPException(502, detail=str(exc)) from exc
    return {"code": "OK", "data": history.public_answer(data)}

LOG = logging.getLogger("uvicorn.error")


@router.post("/query/stream")
async def agent_query_stream(body: AgentQuery, user: User | None = Depends(get_optional_user)):
    if body.runId is None:
        raise HTTPException(422, detail="runId is required")
    check_public_test(body.modelMode, body.publicGatewayConsent)
    if user is None:
        raise HTTPException(401, detail="Agent login is required")
    if body.conversationId is None:
        raise HTTPException(422, detail="conversationId is required")
    if body.sessionId:
        raise HTTPException(400, detail="Provider session is server-owned")
    runtime = EmbeddedAgentGateway()
    run_id = str(body.runId)
    persisted = body.conversationId is not None
    replay = False
    effective_session = None

    if persisted:
        if user is None:
            raise HTTPException(401, detail="Authentication required for server history")
        with SessionLocal() as db:
            conv = history.owned(db, user.id, str(body.conversationId))
            if conv.task_tier != body.taskTier:
                raise HTTPException(409, "Cannot mix task tiers within a conversation")
            effective_session = conv.session_id  # Server owns the resumable session.
            previous, replay = history.reserve(
                db, user.id, conv.id, run_id, body.question.strip(), body.modelMode,
                display_question=body.displayQuestion,
            )
    if replay:
        async def cached():
            yield (json.dumps({"type": "started", "runId": run_id}, ensure_ascii=False) + "\n").encode("utf-8")
            if previous.status == "completed" and previous.result_json:
                yield (json.dumps({
                    "type": "result",
                    "result": history.public_answer(json.loads(previous.result_json)),
                }, ensure_ascii=False) + "\n").encode("utf-8")
            elif previous.status == "cancelled":
                yield b'{"type":"cancelled"}\n'
            else:
                yield (json.dumps({"type": "error", "message": "该次任务已结束，未产生可采信结果。",
                                   "runStatus": previous.status}, ensure_ascii=False) + "\n").encode("utf-8")
        return StreamingResponse(cached(), media_type="application/x-ndjson")

    status = await runtime.status(body.modelMode, body.taskTier)
    if not status.ready:
        if persisted:
            history.transition(run_id, "failed", error="Agent runtime not ready")
        raise HTTPException(503, detail=status.reason or "Agent runtime is not ready")

    async def events():
        terminal = False
        try:
            async for line in runtime.stream(
                body.question.strip(), run_id=run_id, session_id=effective_session,
                model_mode=body.modelMode, public_gateway_consent=body.publicGatewayConsent,
                task_tier=body.taskTier,
            ):
                try:
                    event = json.loads(line)
                except (ValueError, TypeError):
                    raise AgentRuntimeError("Invalid Agent NDJSON event")
                event_type = event.get("type") if isinstance(event, dict) else None
                if event_type == "started":
                    if persisted:
                        history.transition(run_id, "running")
                elif event_type == "activity":
                    item = event.get("event")
                    if isinstance(item, dict) and item.get("type") == "debug_event":
                        if persisted:
                            history.append_debug_event(run_id, item)
                        # Detailed traces are persisted for the admin workbench and
                        # are deliberately not forwarded into the ordinary chat UI.
                        continue
                    if persisted:
                        history.append_activity(run_id, event)
                    # The ordinary chat stream only receives allowlisted tool metadata.
                    if (not isinstance(item, dict) or item.get("type") not in ("tool_call", "tool_result")
                        or item.get("tool") not in history.TOOL_NAMES):
                        continue
                    event = {"type": "activity", "event": {
                        key: item[key] for key in ("type", "callId", "tool", "status") if key in item
                    }}
                elif event_type == "result":
                    result = event.get("result")
                    if not isinstance(result, dict) or result.get("sqlExecuted") is True or result.get("hiddenReasoningExposed") is True:
                        raise AgentRuntimeError("Agent result violates safety contract")
                    clean = history._safe_answer(result)
                    if persisted:
                        history.transition(run_id, "completed", result=clean)
                    event = {"type": "result", "result": history.public_answer(clean)}
                    terminal = True
                elif event_type == "cancelled":
                    if persisted:
                        history.transition(run_id, "cancelled")
                    terminal = True
                elif event_type == "error":
                    if persisted:
                        history.transition(
                            run_id, "timeout" if event.get("reason") == "timeout" else "failed",
                            error="Gateway reported an Agent error",
                        )
                    terminal = True
                    event = {"type": "error", "message": str(event.get("message", "Agent failed"))[:240]}
                else:
                    continue
                yield (json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
            if not terminal:
                if persisted:
                    history.transition(run_id, "interrupted", error="Stream ended without terminal event")
                yield (json.dumps({"type": "error", "message": "Agent 连接中断，结果未确认。"}, ensure_ascii=False) + "\n").encode("utf-8")
                terminal = True
        except AgentRuntimeError:
            LOG.exception("Agent stream failed")
            if persisted:
                history.transition(run_id, "interrupted", error="Agent stream disconnected")
            yield (json.dumps({
                "type": "error", "message": "Agent 数据流已中断，请查看 Gateway 日志。"
            }, ensure_ascii=False) + "\n").encode("utf-8")
            terminal = True
        finally:
            if persisted and not terminal:
                history.transition(run_id, "interrupted", error="Browser disconnected before terminal event")

    return StreamingResponse(
        events(), media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
    )


@router.get("/runs/{run_id}")
async def agent_run_status(run_id: UUID, user: User = Depends(get_optional_user)):
    if user is None:
        raise HTTPException(401, "Authentication required")
    with SessionLocal() as db:
        turn = db.get(AgentTurn, str(run_id))
        if turn is None:
            raise HTTPException(404, "Agent run not found")
        history.owned(db, user.id, turn.conversation_id)
        return {"code": "OK", "data": {
            "runId": turn.id, "conversationId": turn.conversation_id,
            "status": turn.status, "modelMode": turn.model_mode,
        }}


@router.post("/query/{run_id}/cancel")
async def agent_cancel(run_id: UUID, user: User = Depends(get_current_user)):
    with SessionLocal() as db:
        turn = db.get(AgentTurn, str(run_id))
        if turn is None:
            raise HTTPException(404, "Agent run not found")
        if turn is not None:
            history.owned(db, user.id, turn.conversation_id)
            if turn.status in history.TERMINAL:
                return {"code": "OK", "data": {"cancelled": False, "status": turn.status}}
    cancelled = await EmbeddedAgentGateway().cancel(str(run_id))
    if cancelled and turn is not None:
        history.transition(str(run_id), "cancel_requested")
    return {"code": "OK", "data": {
        "cancelled": cancelled, "status": "cancel_requested" if cancelled else "unknown"
    }}
