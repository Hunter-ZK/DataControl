from __future__ import annotations

import asyncio
import json
import shlex
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.app.core.config import (
    AGENT3_MCP_URL,
    AGENT_TIMEOUT_SECONDS,
    AGENT_WORKSPACE,
    DSH_COMMAND,
    MODEL_NAME,
    MODEL_PROVIDER,
)


class AgentRuntimeError(RuntimeError):
    pass


@dataclass(frozen=True)
class RuntimeStatus:
    ready: bool
    dshExecutable: str | None
    command: str
    agent3McpConfigured: bool
    agent3McpUrl: str | None
    provider: str
    model: str
    reason: str | None = None


class DshAcpRuntime:
    """Minimal, guarded ACP stdio bridge for DeepSeek Harness.

    It never executes SQL itself. Agent3 is attached only as an MCP server and is
    expected to expose read-only metadata/SQL-generation/validation tools.
    """

    def __init__(self) -> None:
        self.command = DSH_COMMAND
        self.workspace = AGENT_WORKSPACE
        self.agent3_mcp_url = AGENT3_MCP_URL.strip()
        self.timeout = AGENT_TIMEOUT_SECONDS

    def status(self) -> RuntimeStatus:
        argv = shlex.split(self.command, posix=True)
        executable = shutil.which(argv[0]) if argv else None
        ready = bool(executable and self.agent3_mcp_url)
        reason = None
        if not executable:
            reason = f"dsh launcher not found: {argv[0] if argv else 'empty command'}"
        elif not self.agent3_mcp_url:
            reason = "DATACONTROL_AGENT3_MCP_URL is not configured"
        return RuntimeStatus(
            ready=ready,
            dshExecutable=executable,
            command=self.command,
            agent3McpConfigured=bool(self.agent3_mcp_url),
            agent3McpUrl=self.agent3_mcp_url or None,
            provider=MODEL_PROVIDER,
            model=MODEL_NAME,
            reason=reason,
        )

    async def _write(self, process: asyncio.subprocess.Process, payload: dict[str, Any]) -> None:
        if process.stdin is None:
            raise AgentRuntimeError("ACP stdin is unavailable")
        process.stdin.write((json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8"))
        await process.stdin.drain()

    async def _read_until_response(
        self,
        process: asyncio.subprocess.Process,
        request_id: int,
        events: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if process.stdout is None:
            raise AgentRuntimeError("ACP stdout is unavailable")

        while True:
            line = await process.stdout.readline()
            if not line:
                stderr = ""
                if process.stderr is not None:
                    try:
                        stderr = (await process.stderr.read()).decode("utf-8", errors="replace")[-2000:]
                    except Exception:
                        stderr = ""
                raise AgentRuntimeError(f"dsh ACP process exited before response. {stderr}".strip())
            try:
                message = json.loads(line.decode("utf-8"))
            except json.JSONDecodeError:
                # stdout is reserved for ACP frames; ignore malformed diagnostic noise
                # rather than ever surfacing it as model output.
                continue

            if message.get("method") == "session/update":
                update = (message.get("params") or {}).get("update") or message.get("params") or {}
                update_type = str(update.get("sessionUpdate") or update.get("type") or "update")
                # Never surface hidden reasoning/thought streams.
                lowered = update_type.lower()
                if "thought" in lowered or "reason" in lowered:
                    continue
                content = update.get("content") or {}
                text = content.get("text") if isinstance(content, dict) else None
                event: dict[str, Any] = {"type": update_type}
                if text:
                    event["text"] = text
                tool = update.get("toolCall") or update.get("tool_call")
                if tool:
                    event["tool"] = tool
                events.append(event)
                continue

            if message.get("method") == "session/request_permission":
                # DataControl runs a read-only Agent3 tool surface. Unexpected approval
                # prompts are rejected by policy instead of being auto-approved.
                if "id" in message:
                    await self._write(
                        process,
                        {
                            "jsonrpc": "2.0",
                            "id": message["id"],
                            "error": {"code": -32001, "message": "Permission denied by DataControl read-only policy"},
                        },
                    )
                events.append({"type": "permission_denied"})
                continue

            if message.get("id") == request_id:
                if "error" in message:
                    raise AgentRuntimeError(str(message["error"]))
                return message.get("result") or {}

    async def _request(
        self,
        process: asyncio.subprocess.Process,
        request_id: int,
        method: str,
        params: dict[str, Any],
        events: list[dict[str, Any]],
    ) -> dict[str, Any]:
        await self._write(
            process,
            {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params},
        )
        return await self._read_until_response(process, request_id, events)

    async def run(self, prompt: str) -> dict[str, Any]:
        status = self.status()
        if not status.ready:
            raise AgentRuntimeError(status.reason or "Agent runtime is not ready")

        argv = shlex.split(self.command, posix=True)
        process = await asyncio.create_subprocess_exec(
            *argv,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(Path(self.workspace)),
        )
        events: list[dict[str, Any]] = [{"type": "runtime_started"}]
        try:
            async with asyncio.timeout(self.timeout):
                init = await self._request(
                    process,
                    1,
                    "initialize",
                    {
                        "protocolVersion": 1,
                        "clientCapabilities": {},
                        "clientInfo": {"name": "DataControl", "version": "0.4.0-p3"},
                    },
                    events,
                )
                events.append({"type": "initialized", "protocolVersion": init.get("protocolVersion")})

                session = await self._request(
                    process,
                    2,
                    "session/new",
                    {
                        "cwd": str(Path(self.workspace)),
                        "mcpServers": [
                            {
                                "type": "http",
                                "name": "agent3",
                                "url": self.agent3_mcp_url,
                            }
                        ],
                    },
                    events,
                )
                session_id = session.get("sessionId")
                if not session_id:
                    raise AgentRuntimeError("dsh ACP did not return a sessionId")
                events.append({"type": "session_ready", "sessionId": session_id})

                result = await self._request(
                    process,
                    3,
                    "session/prompt",
                    {
                        "sessionId": session_id,
                        "prompt": [{"type": "text", "text": prompt}],
                    },
                    events,
                )
                answer = "".join(x.get("text", "") for x in events if x.get("text"))
                return {
                    "sessionId": session_id,
                    "answer": answer.strip(),
                    "stopReason": result.get("stopReason"),
                    "events": events,
                    "sqlExecuted": False,
                }
        except TimeoutError as exc:
            raise AgentRuntimeError(f"Agent request exceeded {self.timeout:g}s timeout") from exc
        finally:
            if process.returncode is None:
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=3)
                except TimeoutError:
                    process.kill()
                    await process.wait()
