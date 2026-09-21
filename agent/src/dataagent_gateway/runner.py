from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

import httpx


class HarnessRunError(RuntimeError):
    pass


MCP_TOOL_SUFFIXES = {
    "search_tables",
    "get_schema",
    "get_semantic_model",
    "resolve_metric",
    "search_verified_sql",
    "validate_sql",
    "explain_sql",
    "compile_query",
    "submit_ddl",
}

_LOOPBACK_NO_PROXY = ("127.0.0.1", "localhost", "::1")
_SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


def _with_loopback_no_proxy(env: dict[str, str]) -> dict[str, str]:
    """Preserve external proxy settings while guaranteeing local MCP bypass."""
    current = env.get("NO_PROXY") or env.get("no_proxy") or ""
    values = [item.strip() for item in current.split(",") if item.strip()]
    merged = list(_LOOPBACK_NO_PROXY)
    for value in values:
        if value not in merged:
            merged.append(value)
    joined = ",".join(merged)
    env["NO_PROXY"] = joined
    env["no_proxy"] = joined
    return env


def _tool_suffix(name: str) -> str:
    return name.rsplit("__", 1)[-1]


def _safe_session_id(session_id: str) -> str:
    """Limit DataControl resumes to harness-generated, shell-safe session identifiers."""
    if not _SESSION_ID_PATTERN.fullmatch(session_id):
        raise HarnessRunError("Invalid DataAgent session id")
    return session_id


def _extract_sql_from_text(text: str) -> str | None:
    stripped = text.strip()
    fenced = re.search(r"```(?:sql)?\s*(.+?)```", stripped, flags=re.IGNORECASE | re.DOTALL)
    if fenced:
        candidate = fenced.group(1).strip()
        if re.match(r"^(SELECT|WITH|INSERT|UPDATE|DELETE|MERGE|CREATE|ALTER|DROP|TRUNCATE)\b", candidate, flags=re.IGNORECASE):
            return candidate
    match = re.search(
        r"\b(SELECT|WITH|INSERT|UPDATE|DELETE|MERGE|CREATE|ALTER|DROP|TRUNCATE)\b[\s\S]*",
        stripped,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    candidate = match.group(0).strip()
    if ";" in candidate:
        candidate = candidate.split(";", 1)[0].strip() + ";"
    return candidate


def _extract_sql(value: Any) -> str | None:
    if isinstance(value, dict):
        for key in ("sql", "generated_sql", "generatedSql", "normalized_sql", "normalizedSql"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
        for item in value.values():
            found = _extract_sql(item)
            if found:
                return found
    elif isinstance(value, list):
        for item in value:
            found = _extract_sql(item)
            if found:
                return found
    elif isinstance(value, str):
        return _extract_sql_from_text(value)
    return None


def _json_or_text(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _plain_answer(text: str) -> str:
    """Remove presentation markdown; SQL/evidence are rendered by dedicated UI blocks."""
    value = re.sub(r"```(?:sql)?[\s\S]*?```", "", text, flags=re.IGNORECASE)
    value = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", value)
    value = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", value)
    value = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", value)
    value = re.sub(r"(?m)^\s*[-*+]\s+", "• ", value)
    value = re.sub(r"(?m)^\s*\d+[.)]\s+", "• ", value)
    value = value.replace("**", "").replace("__", "").replace("`", "")
    value = re.sub(r"\n{3,}", "\n\n", value).strip()
    return value


def _dedupe_dicts(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for row in rows:
        value = str(row.get(key) or "")
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(row)
    return out


def _validation_state(sql: str | None, validation: Any) -> str:
    if not sql:
        return "not_applicable"
    if not isinstance(validation, dict):
        return "not_validated"
    if validation.get("valid") is True:
        return "passed"
    if validation.get("valid") is False:
        return "failed"
    return "unknown"


def parse_event_stream(stdout: str) -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    session_id: str | None = None
    final_text = ""
    stop_reason: str | None = None

    # SQL and validation are evidence-bound. We only associate a validation result
    # with the SQL carried by that validate_sql call (or by a compile_query result
    # that embeds its own validation). A later unvalidated compile must not inherit
    # an earlier validation badge.
    sql: str | None = None
    validation: Any = None
    sql_source_call_id: str | None = None
    validation_call_id: str | None = None
    last_compiled_sql: str | None = None
    last_compile_call_id: str | None = None

    call_tools: dict[str, str] = {}
    call_inputs: dict[str, dict[str, Any]] = {}
    metrics: list[dict[str, Any]] = []
    datasets: list[dict[str, Any]] = []
    dimensions: list[str] = []
    period: dict[str, str] | None = None
    caliber: str | None = None
    warnings: list[str] = []

    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue

        event_type = event.get("type")
        if event_type == "session":
            value = event.get("sessionId")
            session_id = value if isinstance(value, str) else session_id
            continue

        if event_type == "final":
            value = event.get("text")
            final_text = value if isinstance(value, str) else ""
            continue

        if event_type == "status":
            if event.get("phase") == "turn_end":
                reason = event.get("reason")
                stop_reason = str(reason) if reason is not None else None
            continue

        if event_type == "tool_call":
            tool = str(event.get("tool") or "")
            suffix = _tool_suffix(tool)
            call_id = str(event.get("callId") or "")
            if suffix in MCP_TOOL_SUFFIXES:
                raw_input = event.get("input")
                tool_input = raw_input if isinstance(raw_input, dict) else {}
                call_tools[call_id] = suffix
                call_inputs[call_id] = tool_input
                events.append({"type": "tool_call", "callId": call_id, "tool": suffix, "input": tool_input})
                if suffix == "compile_query":
                    dimensions = [str(x) for x in tool_input.get("dimensions", []) if str(x)]
                    time_values = [str(x) for x in tool_input.get("time_values", []) if str(x)]
                    if time_values:
                        token = time_values[0]
                        if token.upper() in {"LATEST", "CURRENT"} or token in {"本期", "当期", "当前", "最新", "最近一期"}:
                            period = {"label": "本期 / 最新一期", "resolved": "LATEST"}
                        elif token.upper() in {"PREVIOUS", "PRIOR"} or token in {"上期", "上一期"}:
                            period = {"label": "上期", "resolved": "PREVIOUS"}
                        else:
                            period = {"label": token, "resolved": token}
            continue

        if event_type == "tool_result":
            call_id = str(event.get("callId") or "")
            tool = call_tools.get(call_id)
            if not tool:
                continue
            result = _json_or_text(event.get("result"))
            events.append({"type": "tool_result", "callId": call_id, "tool": tool, "status": event.get("status")})

            if tool == "compile_query":
                compiled_sql = _extract_sql(result)
                if compiled_sql:
                    last_compiled_sql = compiled_sql
                    last_compile_call_id = call_id
                if isinstance(result, dict):
                    nested_validation = result.get("validation")
                    if compiled_sql and nested_validation is not None:
                        sql = compiled_sql
                        validation = nested_validation
                        sql_source_call_id = call_id
                        validation_call_id = call_id

            elif tool == "validate_sql":
                # The validate_sql input is the authoritative SQL for this result.
                # Never pair a validation result with an unrelated earlier compile.
                validated_sql = _extract_sql(call_inputs.get(call_id, {})) or _extract_sql(result)
                if validated_sql:
                    sql = validated_sql
                    validation = result
                    sql_source_call_id = call_id
                    validation_call_id = call_id

            if isinstance(result, dict):
                if tool in {"resolve_metric", "get_semantic_model"}:
                    metric = result.get("metric")
                    if isinstance(metric, dict):
                        row = {
                            "code": metric.get("id"),
                            "name": metric.get("name"),
                            "sourceEntity": metric.get("source_entity"),
                            "measure": metric.get("measure"),
                            "timeField": metric.get("time_field"),
                            "validDimensions": metric.get("valid_dimensions") or [],
                        }
                        metrics.append(row)
                        if metric.get("source_entity"):
                            datasets.append({"tableName": metric.get("source_entity"), "name": metric.get("source_entity")})
                        if metric.get("caveats"):
                            caliber = str(metric.get("caveats"))
                elif tool == "search_tables":
                    for table in result.get("tables", []) if isinstance(result.get("tables"), list) else []:
                        if isinstance(table, dict):
                            datasets.append({"tableName": table.get("full_name"), "name": table.get("description") or table.get("full_name")})
                elif tool == "get_schema" and result.get("found"):
                    datasets.append({"tableName": result.get("table"), "name": result.get("description") or result.get("table")})
                    for warning in result.get("warnings", []) if isinstance(result.get("warnings"), list) else []:
                        warnings.append(str(warning))
            continue

        # Deliberately drop thinking and intermediate model text events.

    if not final_text.strip():
        raise HarnessRunError("dsh completed without a final assistant answer")

    # A compiled SQL can be shown even before validation, but it must be explicitly
    # marked not_validated instead of inheriting a previous validation result.
    if sql is None and last_compiled_sql:
        sql = last_compiled_sql
        sql_source_call_id = last_compile_call_id
        validation = None
        validation_call_id = None

    answer = _plain_answer(final_text)
    if not answer:
        answer = "已完成分析。请查看下方指标、资产、SQL 与校验结果。"

    return {
        "sessionId": session_id,
        "answer": answer,
        "summary": answer.split("\n", 1)[0][:500],
        "stopReason": stop_reason,
        "events": events,
        "sql": sql,
        "validation": validation,
        "validationState": _validation_state(sql, validation),
        "sqlSourceCallId": sql_source_call_id,
        "validationCallId": validation_call_id,
        "evidence": {
            "metrics": _dedupe_dicts(metrics, "code"),
            "datasets": _dedupe_dicts(datasets, "tableName"),
            "dimensions": list(dict.fromkeys(dimensions)),
            "period": period,
            "caliber": caliber,
            "warnings": list(dict.fromkeys(warnings)),
        },
        "sqlExecuted": False,
        "hiddenReasoningExposed": False,
    }


class HeadlessHarnessRunner:
    def __init__(self, *, timeout_seconds: float | None = None) -> None:
        self.repo_root = Path(__file__).resolve().parents[3]
        self.agent_root = self.repo_root / "agent"
        self.timeout_seconds = timeout_seconds or float(os.getenv("DATACONTROL_AGENT_RUN_TIMEOUT", "120"))
        self.dsh_home = Path(os.getenv("DSH_HOME", str(self.repo_root / ".local" / "dsh-home"))).resolve()
        suffix = "dsh.cmd" if os.name == "nt" else "dsh"
        self.dsh_bin = self.agent_root / "dsh" / "node_modules" / ".bin" / suffix
        self.profile = os.getenv("DATACONTROL_DSH_PROFILE", "dataagent-headless")

    @property
    def profile_dir(self) -> Path:
        return self.dsh_home / "profiles" / self.profile

    async def _mcp_reachable(self) -> bool:
        try:
            # MCP is always local. Do not let HTTP(S)_PROXY/ALL_PROXY intercept 8900.
            async with httpx.AsyncClient(timeout=1.0, trust_env=False) as client:
                await client.get("http://127.0.0.1:8900/mcp")
            return True
        except httpx.HTTPError:
            return False

    async def health(self) -> dict[str, Any]:
        dsh_installed = self.dsh_bin.exists()
        profile_ready = (self.profile_dir / "package.json").exists()
        api_key_present = bool(os.getenv("DEEPSEEK_API_KEY"))
        mcp_reachable = await self._mcp_reachable()
        ready = dsh_installed and profile_ready and api_key_present and mcp_reachable
        blockers: list[str] = []
        if not dsh_installed:
            blockers.append("DeepSeek Harness is not installed")
        if not profile_ready:
            blockers.append(f"dsh profile '{self.profile}' is not initialized")
        if not api_key_present:
            blockers.append("DEEPSEEK_API_KEY is not set")
        if not mcp_reachable:
            blockers.append("Agent3 MCP is not reachable on 127.0.0.1:8900")
        return {
            "ready": ready,
            "dshInstalled": dsh_installed,
            "profileReady": profile_ready,
            "apiKeyPresent": api_key_present,
            "mcpReachable": mcp_reachable,
            "profile": self.profile,
            "reason": "; ".join(blockers) if blockers else None,
        }

    def _command(self, session_id: str | None) -> list[str]:
        # The user prompt is deliberately absent from argv and is sent through
        # stdin instead. dsh-headless officially reads the task from stdin when
        # no positional task is supplied.
        command = [str(self.dsh_bin), "--profile", self.profile, "--json"]
        if session_id:
            command.extend(["--session-id", _safe_session_id(session_id)])
        return command

    async def _spawn(self, command: list[str], env: dict[str, str]):
        process_kwargs = {
            "cwd": self.repo_root,
            "env": env,
            "stdin": asyncio.subprocess.PIPE,
            "stdout": asyncio.subprocess.PIPE,
            "stderr": asyncio.subprocess.PIPE,
        }
        if os.name == "nt":
            # npm exposes dsh as dsh.cmd on Windows. The only dynamic argv value
            # is the validated session id; the untrusted user question is stdin.
            cmdline = subprocess.list2cmdline(command)
            return await asyncio.create_subprocess_exec("cmd.exe", "/d", "/s", "/c", cmdline, **process_kwargs)
        return await asyncio.create_subprocess_exec(*command, **process_kwargs)

    async def run(self, question: str, *, session_id: str | None = None) -> dict[str, Any]:
        if not question.strip():
            raise HarnessRunError("DataAgent question cannot be empty")

        health = await self.health()
        if not health["ready"]:
            raise HarnessRunError(str(health["reason"] or "DataAgent runtime is not ready"))

        env = _with_loopback_no_proxy(os.environ.copy())
        env["DSH_HOME"] = str(self.dsh_home)
        env["DSH_TELEMETRY_MODE"] = "DISABLED"
        process = await self._spawn(self._command(session_id), env)
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=question.encode("utf-8")),
                timeout=self.timeout_seconds,
            )
        except TimeoutError as exc:
            process.kill()
            await process.wait()
            raise HarnessRunError(f"dsh request exceeded {self.timeout_seconds:g}s timeout") from exc

        stdout_text = stdout.decode("utf-8", errors="replace")
        stderr_text = stderr.decode("utf-8", errors="replace")
        if process.returncode != 0:
            detail = stderr_text.strip()[-1600:] or "dsh exited without diagnostics"
            raise HarnessRunError(f"dsh exited with code {process.returncode}: {detail}")
        return parse_event_stream(stdout_text)
