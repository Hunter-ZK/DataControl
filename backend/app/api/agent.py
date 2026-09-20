from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.app.agent.runtime import AgentRuntimeError, DshAcpRuntime

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])


class AgentQuery(BaseModel):
    question: str = Field(min_length=2, max_length=4000)


@router.get("/status")
def agent_status():
    status = DshAcpRuntime().status()
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
    runtime = DshAcpRuntime()
    if not runtime.status().ready:
        status = runtime.status()
        raise HTTPException(
            503,
            detail={
                "message": "Intelligent Q&A runtime is not ready",
                "reason": status.reason,
                "agent3McpConfigured": status.agent3McpConfigured,
            },
        )
    try:
        data = await runtime.run(body.question.strip())
    except AgentRuntimeError as exc:
        raise HTTPException(502, detail=str(exc)) from exc
    return {"code": "OK", "data": data}
