from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.app.agent.runtime import AgentRuntimeError, EmbeddedAgentGateway

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])


class AgentQuery(BaseModel):
    question: str = Field(min_length=2, max_length=4000)


@router.get("/status")
async def agent_status():
    status = await EmbeddedAgentGateway().status()
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
    runtime = EmbeddedAgentGateway()
    status = await runtime.status()
    if not status.ready:
        raise HTTPException(
            503,
            detail={
                "message": "Intelligent Q&A runtime is not ready",
                "reason": status.reason,
                "mode": status.mode,
                "source": status.source,
                "integrated": status.integrated,
                "serviceReachable": status.serviceReachable,
            },
        )
    try:
        data = await runtime.run(body.question.strip())
    except AgentRuntimeError as exc:
        raise HTTPException(502, detail=str(exc)) from exc
    return {"code": "OK", "data": data}
