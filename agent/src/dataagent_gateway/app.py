from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from dataagent_gateway.runner import HarnessRunError, HeadlessHarnessRunner

app = FastAPI(title="DataControl Embedded DataAgent Gateway", version="0.3.0-p3")


class QueryRequest(BaseModel):
    question: str = Field(min_length=2, max_length=4000)
    sessionId: str | None = Field(default=None, max_length=200)


@app.get("/health")
async def health():
    status = await HeadlessHarnessRunner().health()
    return {
        "status": "ok" if status["ready"] else "degraded",
        "component": "embedded-dataagent-gateway",
        "sqlExecutionEnabled": False,
        "hiddenReasoningExposed": False,
        **status,
    }


@app.post("/v1/query")
async def query(body: QueryRequest):
    runner = HeadlessHarnessRunner()
    try:
        result = await runner.run(body.question.strip(), session_id=body.sessionId)
    except HarnessRunError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if result.get("sqlExecuted") is True:
        raise HTTPException(status_code=500, detail="SQL execution is forbidden in P3")
    return result
