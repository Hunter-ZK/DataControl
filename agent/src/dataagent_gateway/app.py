from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Literal
from uuid import UUID

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from dataagent_gateway.runner import HarnessRunError, HeadlessHarnessRunner

app = FastAPI(title="DataControl Embedded DataAgent Gateway", version="0.3.0-p3")


class QueryRequest(BaseModel):
    question: str = Field(min_length=2, max_length=4000)
    sessionId: str | None = Field(default=None, max_length=200)
    runId: UUID | None = None
    modelMode: Literal["deepseek", "free-test"] = "deepseek"
    taskTier: Literal["standard", "multi"] = "standard"
    publicGatewayConsent: bool = False


def allow_public_test(mode: str, consent: bool = False) -> None:
    if mode != "free-test":
        return
    if consent is False:
        raise HTTPException(403, "Public model request requires the client's explicit consent")


@app.get("/health")
async def health(modelMode: Literal["deepseek", "free-test"] | None = None,
                 taskTier: Literal["standard", "multi"] = "standard"):
    status = await HeadlessHarnessRunner(model_mode=modelMode, task_tier=taskTier).health()
    return {
        "status": "ok" if status["ready"] else "degraded",
        "component": "embedded-dataagent-gateway",
        "sqlExecutionEnabled": False,
        "hiddenReasoningExposed": False,
        **status,
    }


@app.post("/v1/query")
async def query(body: QueryRequest):
    allow_public_test(body.modelMode, body.publicGatewayConsent)
    runner = HeadlessHarnessRunner(model_mode=body.modelMode, **(
        {"task_tier": "multi"} if body.taskTier == "multi" else {}
    ))
    try:
        result = await runner.run(body.question.strip(), session_id=body.sessionId)
    except HarnessRunError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if result.get("sqlExecuted") is True:
        raise HTTPException(status_code=500, detail="SQL execution is forbidden in P3")
    return result

# Local, in-process cancellation registry. This is not a distributed job queue;
# a later R1 increment will persist completed sessions and audit records.
ACTIVE_TURNS: dict[str, asyncio.Task[dict[str, Any]]] = {}
LOG = logging.getLogger("uvicorn.error")


def _json_line(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n"


@app.post("/v1/query/stream")
async def query_stream(body: QueryRequest):
    allow_public_test(body.modelMode, body.publicGatewayConsent)
    if body.runId is None:
        raise HTTPException(422, detail="runId is required for cancellation")
    run_id = str(body.runId)
    if run_id in ACTIVE_TURNS:
        raise HTTPException(409, detail="Agent run is already active")
    if sum(not task.done() for task in ACTIVE_TURNS.values()) >= 4:
        raise HTTPException(429, detail="Agent gateway is at its concurrent run limit")
    runner = HeadlessHarnessRunner(model_mode=body.modelMode, **(
        {"task_tier": "multi"} if body.taskTier == "multi" else {}
    ))
    events: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

    def on_activity(activity: dict[str, Any]) -> None:
        events.put_nowait({"type": "activity", "event": activity})

    # Register eagerly: cancellation or a second request can arrive before the
    # StreamingResponse iterator is first consumed.
    task = asyncio.create_task(
        runner.run(body.question.strip(), session_id=body.sessionId, on_activity=on_activity)
    )
    ACTIVE_TURNS[run_id] = task

    def forget_done(done_task: asyncio.Task[dict[str, Any]]) -> None:
        if ACTIVE_TURNS.get(run_id) is done_task:
            ACTIVE_TURNS.pop(run_id, None)

    task.add_done_callback(forget_done)

    async def stream():
        try:
            yield _json_line({"type": "started", "runId": run_id})
            while not task.done() or not events.empty():
                try:
                    update = await asyncio.wait_for(events.get(), timeout=0.25)
                    yield _json_line(update)
                except TimeoutError:
                    continue
            try:
                answer = await task
                yield _json_line({"type": "result", "result": answer})
            except asyncio.CancelledError:
                yield _json_line({"type": "cancelled"})
            except HarnessRunError as exc:
                LOG.exception("[AgentStream:%s] task failed", run_id[:8])
                reason = "timeout" if "exceeded" in str(exc).lower() or "timeout" in str(exc).lower() else "failed"
                yield _json_line({"type": "error", "reason": reason, "message": "Agent 处理失败，请查看服务端日志。"})
            except Exception:
                LOG.exception("[AgentStream:%s] unexpected failure", run_id[:8])
                yield _json_line({"type": "error", "message": "Agent 处理异常，请查看服务端日志。"})
        finally:
            if ACTIVE_TURNS.get(run_id) is task:
                ACTIVE_TURNS.pop(run_id, None)
            if not task.done():
                task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    return StreamingResponse(
        stream(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
    )


@app.post("/v1/query/{run_id}/cancel")
async def cancel_query(run_id: UUID):
    task = ACTIVE_TURNS.get(str(run_id))
    if task and not task.done():
        task.cancel()
        return {"cancelled": True}
    return {"cancelled": False}
