from __future__ import annotations

import asyncio
import json
import logging
import time
from ipaddress import ip_address
from typing import Any, Literal
from uuid import UUID

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from dataagent_gateway.runner import HarnessRunError, HeadlessHarnessRunner, _debug_capture_enabled
from dataagent_gateway.quick import LocalQuickFailure, LocalQuickRunner

app = FastAPI(title="DataControl Embedded DataAgent Gateway", version="0.3.0-p3")


class QueryRequest(BaseModel):
    question: str = Field(min_length=2, max_length=4000)
    sessionId: str | None = Field(default=None, max_length=200)
    runId: UUID | None = None
    modelMode: Literal["deepseek", "free-test", "local-deepseek"] = "deepseek"
    taskTier: Literal["standard", "multi", "quick"] = "standard"
    publicGatewayConsent: bool = False
    quickMaxTokens: Literal[128, 256, 512] = 256


def allow_public_test(mode: str, consent: bool = False) -> None:
    if mode != "free-test":
        return
    if consent is False:
        raise HTTPException(403, "Public model request requires the client's explicit consent")


@app.get("/health")
async def health(modelMode: Literal["deepseek", "free-test", "local-deepseek"] | None = None,
                 taskTier: Literal["standard", "multi", "quick"] = "standard"):
    if taskTier == "quick":
        if modelMode != "local-deepseek":
            raise HTTPException(422, "Quick mode only supports local DeepSeek")
        status = await LocalQuickRunner().health()
    else:
        status = await HeadlessHarnessRunner(model_mode=modelMode, task_tier=taskTier).health()
    return {
        "status": "ok" if status["ready"] else "degraded",
        "component": "embedded-dataagent-gateway",
        "sqlExecutionEnabled": False,
        "hiddenReasoningExposed": False,
        **status,
    }


@app.get("/v1/debug/config")
async def debug_config(
    request: Request,
    modelMode: Literal["deepseek", "free-test", "local-deepseek"] = "deepseek",
    taskTier: Literal["standard", "multi", "quick"] = "standard",
):
    """Loopback-only config inventory for the authenticated Portal admin workbench."""
    host = request.client.host if request.client else ""
    try:
        is_loopback = ip_address(host).is_loopback
    except ValueError:
        is_loopback = host == "testclient"
    if not is_loopback:
        raise HTTPException(403, "Debug configuration is available only over loopback")
    if taskTier == "quick":
        if modelMode != "local-deepseek":
            raise HTTPException(422, "Quick mode only supports local DeepSeek")
        status = await LocalQuickRunner().health()
        return {
            "captureEnabled": _debug_capture_enabled(),
            "apiKeyPresent": False,
            "modelMode": modelMode, "taskTier": "quick",
            "provider": status["provider"], "model": status["model"],
            "profile": "local-quick-direct", "profileDir": "",
            "timeoutSeconds": 240, "sqlExecutionEnabled": False,
            "hiddenReasoningCaptured": False, "files": [],
            "limitations": [
                "极速回答仅调用本地模型一次，不调用 dsh/MCP，不查询真实元数据或校验 SQL。",
                "请求尝试将思考预算设为零，是否生效取决于 llama.cpp 版本及聊天模板。",
            ],
        }
    runner = HeadlessHarnessRunner(
        model_mode=modelMode,
        **({"task_tier": "multi"} if taskTier == "multi" else {}),
    )
    return runner.debug_config()


@app.post("/v1/query")
async def query(body: QueryRequest):
    allow_public_test(body.modelMode, body.publicGatewayConsent)
    if body.taskTier == "quick" and body.modelMode != "local-deepseek":
        raise HTTPException(422, "Quick mode only supports local DeepSeek")
    runner = (
        LocalQuickRunner(body.quickMaxTokens) if body.taskTier == "quick"
        else HeadlessHarnessRunner(model_mode=body.modelMode, **(
            {"task_tier": "multi"} if body.taskTier == "multi" else {}
        ))
    )
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
ACTIVE_LOCAL_TURNS: set[str] = set()
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
    if body.modelMode == "local-deepseek" and any(
        not ACTIVE_TURNS[local_id].done()
        for local_id in ACTIVE_LOCAL_TURNS if local_id in ACTIVE_TURNS
    ):
        raise HTTPException(429, detail="Local CPU model allows one active Agent task; stop or finish the previous run")
    if body.taskTier == "quick" and body.modelMode != "local-deepseek":
        raise HTTPException(422, "Quick mode only supports local DeepSeek")
    runner = (
        LocalQuickRunner(body.quickMaxTokens) if body.taskTier == "quick"
        else HeadlessHarnessRunner(model_mode=body.modelMode, **(
            {"task_tier": "multi"} if body.taskTier == "multi" else {}
        ))
    )
    events: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

    def on_activity(activity: dict[str, Any]) -> None:
        events.put_nowait({"type": "activity", "event": activity})

    # Register eagerly: cancellation or a second request can arrive before the
    # StreamingResponse iterator is first consumed.
    task = asyncio.create_task(
        runner.run(body.question.strip(), session_id=body.sessionId, on_activity=on_activity)
    )
    ACTIVE_TURNS[run_id] = task
    if body.modelMode == "local-deepseek":
        ACTIVE_LOCAL_TURNS.add(run_id)

    def forget_done(done_task: asyncio.Task[dict[str, Any]]) -> None:
        if ACTIVE_TURNS.get(run_id) is done_task:
            ACTIVE_TURNS.pop(run_id, None)
            ACTIVE_LOCAL_TURNS.discard(run_id)

    task.add_done_callback(forget_done)

    async def stream():
        started = time.monotonic()
        last_heartbeat = started
        try:
            yield _json_line({"type": "started", "runId": run_id})
            while not task.done() or not events.empty():
                try:
                    update = await asyncio.wait_for(events.get(), timeout=0.25)
                    yield _json_line(update)
                except TimeoutError:
                    now = time.monotonic()
                    if now - last_heartbeat >= 10:
                        yield _json_line({
                            "type": "heartbeat", "runId": run_id,
                            "elapsedMs": int((now - started) * 1000),
                        })
                        last_heartbeat = now
                    continue
            try:
                answer = await task
                yield _json_line({"type": "result", "result": answer})
            except asyncio.CancelledError:
                yield _json_line({"type": "cancelled"})
            except LocalQuickFailure as exc:
                LOG.warning("[AgentStream:%s] local quick failure: %s", run_id[:8], exc.code)
                yield _json_line({
                    "type": "error", "reason": "timeout" if exc.code == "LOCAL_TIMEOUT" else "failed",
                    "code": exc.code, "message": exc.user_message,
                })
            except HarnessRunError as exc:
                LOG.exception("[AgentStream:%s] task failed", run_id[:8])
                lower = str(exc).lower()
                if "exceeded" in lower or "timeout" in lower:
                    reason, code = "timeout", "HARNESS_TIMEOUT"
                    message = "完整 Agent 推理超时。当前 CPU 模型速度较低，可改用极速回答测试基础能力。"
                elif "without a final assistant answer" in lower:
                    reason, code = "failed", "HARNESS_NO_FINAL_ANSWER"
                    message = "模型未生成 Harness 可识别的最终回答；可能是模型/模板不兼容或工具调用能力不足。请查看管理员 Trace。"
                elif "dsh exited with code" in lower:
                    reason, code = "failed", "HARNESS_EXIT_ERROR"
                    message = "dsh Harness 进程异常退出。请查看管理员 Trace 中的 stderr 和本地 Gateway 日志。"
                else:
                    reason, code = "failed", "HARNESS_FAILURE"
                    message = "完整 Agent 执行失败，请查看管理员工作台 Trace 或 Gateway 日志。"
                yield _json_line({
                    "type": "error", "reason": reason, "code": code, "message": message,
                })
            except Exception:
                LOG.exception("[AgentStream:%s] unexpected failure", run_id[:8])
                yield _json_line({"type": "error", "message": "Agent 处理异常，请查看服务端日志。"})
        finally:
            if ACTIVE_TURNS.get(run_id) is task:
                ACTIVE_TURNS.pop(run_id, None)
                ACTIVE_LOCAL_TURNS.discard(run_id)
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
