from __future__ import annotations

from dataclasses import asdict
import json
import logging
from uuid import UUID
from typing import Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.app.agent.runtime import AgentRuntimeError, EmbeddedAgentGateway

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])


class AgentQuery(BaseModel):
    question: str = Field(min_length=2, max_length=4000)
    sessionId: str | None = Field(default=None, max_length=200)
    runId: UUID | None = None
    modelMode: Literal["deepseek", "free-test"] = "deepseek"
    publicGatewayConsent: bool = False


@router.get("/status")
async def agent_status(modelMode: Literal["deepseek", "free-test"] = "deepseek"):
    status = await EmbeddedAgentGateway().status(modelMode)
    return {
        "code": "OK",
        "data": {
            **asdict(status),
            "sqlExecutionEnabled": False,
            "hiddenReasoningExposed": False,
        },
    }


@router.post("/query")
async def agent_query(body: AgentQuery):
    if body.modelMode == "free-test" and not body.publicGatewayConsent:
        raise HTTPException(403, detail="Free-test public gateway requires explicit consent")
    runtime = EmbeddedAgentGateway()
    status = await runtime.status(body.modelMode)
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
        )
    except AgentRuntimeError as exc:
        raise HTTPException(502, detail=str(exc)) from exc
    return {"code": "OK", "data": data}

LOG = logging.getLogger("uvicorn.error")


@router.post("/query/stream")
async def agent_query_stream(body: AgentQuery):
    if body.runId is None:
        raise HTTPException(422, detail="runId is required")
    if body.modelMode == "free-test" and not body.publicGatewayConsent:
        raise HTTPException(403, detail="Free-test public gateway requires explicit consent")
    runtime = EmbeddedAgentGateway()
    status = await runtime.status(body.modelMode)
    if not status.ready:
        raise HTTPException(503, detail=status.reason or "Agent runtime is not ready")

    async def events():
        try:
            async for line in runtime.stream(
                body.question.strip(), run_id=str(body.runId), session_id=body.sessionId,
                model_mode=body.modelMode, public_gateway_consent=body.publicGatewayConsent
            ):
                yield line
        except AgentRuntimeError:
            LOG.exception("Agent stream failed")
            yield (json.dumps({
                "type": "error", "message": "Agent 数据流已中断，请查看 Gateway 日志。"
            }, ensure_ascii=False) + "\n").encode("utf-8")

    return StreamingResponse(
        events(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
    )


@router.post("/query/{run_id}/cancel")
async def agent_cancel(run_id: UUID):
    cancelled = await EmbeddedAgentGateway().cancel(str(run_id))
    return {"code": "OK", "data": {"cancelled": cancelled}}
