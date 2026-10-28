"""R1 streaming/cancellation contracts: no raw model data in activity updates."""
from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

from dataagent_gateway.app import ACTIVE_TURNS, cancel_query, query_stream, QueryRequest
from dataagent_gateway.runner import HeadlessHarnessRunner


def test_live_activity_projects_only_allowlisted_tool_and_status():
    secret = "user-sensitive-SQL-secret"
    seen: list[dict] = []

    async def collect():
        reader = asyncio.StreamReader()
        items = [
            {"type": "thinking", "text": secret},
            {"type": "tool_call", "callId": "a1", "tool": "mcp__agent3__resolve_metric",
             "input": {"sql": secret}},
            {"type": "tool_result", "callId": "a1", "status": "completed",
             "result": {"answer": secret}},
            {"type": "tool_call", "callId": "b1", "tool": "tool-bash",
             "input": {"command": secret}},
            {"type": "tool_result", "callId": "b1", "status": "failed",
             "result": secret},
            {"type": "final", "text": secret},
        ]
        reader.feed_data(("\n".join(json.dumps(x) for x in items)+"\n").encode())
        reader.feed_eof()
        return await HeadlessHarnessRunner()._capture_trace(reader, "safe-id", seen.append)

    raw = asyncio.run(collect())
    assert secret in raw  # raw stream is used only internally for final result parsing
    assert seen == [
        {"type": "tool_call", "callId": "a1", "tool": "resolve_metric"},
        {"type": "tool_result", "callId": "a1", "tool": "resolve_metric", "status": "completed"},
    ]
    assert secret not in json.dumps(seen)


def test_cancel_endpoint_cancels_server_task():
    # Direct route function uses runtime UUID parsing only on HTTP boundary.
    from uuid import UUID
    async def wrapped():
        run_id = UUID("6be1d2c2-54eb-426d-ab6e-69d5914705f1")
        async def pending():
            await asyncio.Event().wait()
            return {}
        task = asyncio.create_task(pending())
        ACTIVE_TURNS[str(run_id)] = task
        try:
            assert await cancel_query(run_id) == {"cancelled": True}
            try:
                await task
            except asyncio.CancelledError:
                pass
            assert task.cancelled()
            assert await cancel_query(run_id) == {"cancelled": False}
        finally:
            ACTIVE_TURNS.pop(str(run_id), None)
    asyncio.run(wrapped())


def test_stream_only_emits_sanitized_events_and_final_result(monkeypatch):
    from uuid import UUID
    import dataagent_gateway.app as gateway_app

    class FakeRunner:
        async def run(self, question, *, session_id=None, on_activity=None):
            assert question == "本期贷款余额"
            on_activity({"type": "tool_call", "callId": "c1", "tool": "resolve_metric"})
            on_activity({"type": "tool_result", "callId": "c1", "tool": "resolve_metric", "status": "completed"})
            return {
                "sessionId": "safe-session",
                "answer": "可信结论",
                "sqlExecuted": False,
                "hiddenReasoningExposed": False,
            }

    monkeypatch.setattr(gateway_app, "HeadlessHarnessRunner", FakeRunner)
    async def scenario():
        response = await query_stream(QueryRequest(
            question="本期贷款余额",
            runId=UUID("a2114722-952b-48e0-bd09-88497178da8b"),
        ))
        chunks = [json.loads(chunk) async for chunk in response.body_iterator]
        assert [item["type"] for item in chunks] == ["started", "activity", "activity", "result"]
        assert chunks[-1]["result"]["answer"] == "可信结论"
        assert chunks[1]["event"]["tool"] == "resolve_metric"
        assert all("input" not in item for item in chunks)
        assert not ACTIVE_TURNS

    asyncio.run(scenario())


def test_cancelled_runner_kills_child_process(monkeypatch):
    async def scenario():
        runner = HeadlessHarnessRunner()
        async def ready():
            return {"ready": True}
        monkeypatch.setattr(runner, "health", ready)
        child_done = asyncio.Event()
        class FakeProcess:
            def __init__(self):
                self.returncode = None
                self.stdout = asyncio.StreamReader()
                self.stderr = asyncio.StreamReader()
                self.stdin = SimpleNamespace(write=lambda b: None, drain=self.drain, close=lambda: None)
                self.killed = False
            async def drain(self):
                return None
            async def wait(self):
                await child_done.wait()
                return -9
            def kill(self):
                self.killed = True
                self.returncode = -9
                child_done.set()
        process = FakeProcess()
        async def spawn(*args, **kwargs):
            return process
        monkeypatch.setattr(runner, "_spawn", spawn)
        task = asyncio.create_task(runner.run("test"))
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        assert process.killed
    asyncio.run(scenario())
