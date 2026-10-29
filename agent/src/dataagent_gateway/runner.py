from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
import uuid
from pathlib import Path
from typing import Any, Callable

import httpx


class HarnessRunError(RuntimeError):
    pass


# Uvicorn's configured stderr logger is redirected to .local/agent-gateway.err.log.
# Only bounded event metadata is logged: never prompt, tool inputs, SQL, or reasoning.
LOGGER = logging.getLogger("uvicorn.error")


MCP_TOOL_SUFFIXES = frozenset(json.loads(
    (Path(__file__).resolve().parents[2] / "tool-catalog.json").read_text(encoding="utf-8")
)["tools"])

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
        if re.match(
            r"^(SELECT|WITH|INSERT|UPDATE|DELETE|MERGE|CREATE|ALTER|DROP|TRUNCATE)\b",
            candidate,
            flags=re.IGNORECASE,
        ):
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


def _presentation_answer(text: str) -> str:
    """Preserve safe presentation markdown while removing duplicate SQL/image payloads."""
    value = re.sub(r"```sql\s*[\s\S]*?```", "", text, flags=re.IGNORECASE)
    value = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", value)
    value = re.sub(r"\n{3,}", "\n\n", value).strip()
    return value


def _answer_summary(answer: str) -> str:
    first = answer.split("\n", 1)[0].strip()
    first = re.sub(r"^\s{0,3}#{1,6}\s*", "", first)
    first = re.sub(r"^\s*>\s*", "", first)
    first = re.sub(r"[*_`~]", "", first).strip()
    return first[:500]


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


def _metric_evidence(metric: dict[str, Any]) -> dict[str, Any]:
    return {
        "code": metric.get("id"),
        "name": metric.get("name"),
        "sourceEntity": metric.get("source_entity"),
        "measure": metric.get("measure"),
        "timeField": metric.get("time_field"),
        "validDimensions": metric.get("valid_dimensions") or [],
        "metricKind": metric.get("kind"),
        "timeGrain": metric.get("time_grain"),
    }


def _period_from_tool_input(tool_input: dict[str, Any]) -> dict[str, str] | None:
    time_values = [str(item) for item in tool_input.get("time_values", []) if str(item)]
    if not time_values:
        return None
    token = time_values[0]
    if token.upper() in {"LATEST", "CURRENT"} or token in {
        "本期",
        "当期",
        "当前",
        "最新",
        "最近一期",
    }:
        return {"label": "本期 / 最新一期", "resolved": "LATEST"}
    if token.upper() in {"PREVIOUS", "PRIOR"} or token in {"上期", "上一期"}:
        return {"label": "上期", "resolved": "PREVIOUS"}
    return {"label": token, "resolved": token}


def parse_event_stream(stdout: str) -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    session_id: str | None = None
    final_text = ""
    stop_reason: str | None = None

    # SQL and validation are evidence-bound. Validation may only describe the SQL
    # carried by the same validate/compile result.
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
    assets: list[dict[str, Any]] = []
    code_values: list[dict[str, Any]] = []
    dimensions: list[str] = []
    period: dict[str, str] | None = None
    caliber: str | None = None
    warnings: list[str] = []
    clarification: dict[str, Any] | None = None
    semantic_plan: dict[str, Any] | None = None
    semantic_validation: dict[str, Any] | None = None
    research_policy = "internal_only"

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
                events.append(
                    {"type": "tool_call", "callId": call_id, "tool": suffix, "input": tool_input}
                )
                if suffix == "compile_query":
                    dimensions = [str(item) for item in tool_input.get("dimensions", []) if str(item)]
                    period = _period_from_tool_input(tool_input) or period
            continue

        if event_type == "tool_result":
            call_id = str(event.get("callId") or "")
            tool = call_tools.get(call_id)
            if not tool:
                continue
            result = _json_or_text(event.get("result"))
            events.append(
                {
                    "type": "tool_result",
                    "callId": call_id,
                    "tool": tool,
                    "status": event.get("status"),
                    "output": result,
                }
            )

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
                    candidate_plan = result.get("semanticPlan")
                    if isinstance(candidate_plan, dict):
                        semantic_plan = candidate_plan
                        plan_dimensions = candidate_plan.get("dimensions")
                        if isinstance(plan_dimensions, list):
                            dimensions = [str(item) for item in plan_dimensions if str(item)]
                        policy = candidate_plan.get("researchPolicy")
                        if isinstance(policy, str) and policy:
                            research_policy = policy
                    candidate_semantic_validation = result.get("semanticValidation")
                    if isinstance(candidate_semantic_validation, dict):
                        semantic_validation = candidate_semantic_validation

            elif tool == "validate_sql":
                validated_sql = _extract_sql(call_inputs.get(call_id, {})) or _extract_sql(result)
                if validated_sql:
                    sql = validated_sql
                    validation = result
                    sql_source_call_id = call_id
                    validation_call_id = call_id

            if isinstance(result, dict):
                if tool in {"resolve_metric", "get_semantic_model", "plan_metric"}:
                    metric = result.get("metric")
                    if isinstance(metric, dict):
                        metrics.append(_metric_evidence(metric))
                        if metric.get("source_entity"):
                            datasets.append(
                                {
                                    "tableName": metric.get("source_entity"),
                                    "name": metric.get("source_entity"),
                                }
                            )
                        if metric.get("caveats"):
                            caliber = str(metric.get("caveats"))
                    if tool == "plan_metric":
                        policy = result.get("researchPolicy")
                        if isinstance(policy, str) and policy:
                            research_policy = policy
                        candidate = result.get("clarification")
                        if isinstance(candidate, dict) and result.get("status") in {
                            "clarification_required",
                            "evidence_insufficient",
                        }:
                            clarification = candidate
                elif tool == "resolve_code_value":
                    policy = result.get("researchPolicy")
                    if isinstance(policy, str) and policy:
                        research_policy = policy
                    matches = result.get("matches", [])
                    if isinstance(matches, list) and matches:
                        tool_input = call_inputs.get(call_id, {})
                        code_values.append(
                            {
                                "tableName": result.get("table"),
                                "field": result.get("field"),
                                "phrase": tool_input.get("phrase"),
                                "codeTableNo": result.get("codeTableNo"),
                                "matches": [
                                    {
                                        "value": item.get("value"),
                                        "name": item.get("name"),
                                        "description": item.get("description"),
                                    }
                                    for item in matches
                                    if isinstance(item, dict)
                                ],
                            }
                        )
                elif tool == "search_assets":
                    for row in result.get("assets", [])[:40] if isinstance(result.get("assets"), list) else []:
                        if isinstance(row, dict) and row.get("assetId") and row.get("assetType"):
                            assets.append({
                                "assetId": str(row["assetId"]),
                                "assetType": str(row["assetType"]),
                                "title": str(row.get("title") or row.get("technicalName") or ""),
                                "technicalName": str(row.get("technicalName") or ""),
                                "sourceCallId": call_id,
                            })
                elif tool == "get_asset":
                    if result.get("assetId") and result.get("assetType"):
                        assets.append({
                            "assetId": str(result["assetId"]),
                            "assetType": str(result["assetType"]),
                            "title": str(result.get("title") or ""),
                            "technicalName": str(result.get("technicalName") or ""),
                            "sourceCallId": call_id,
                        })
                elif tool == "search_tables":
                    tables = result.get("tables", [])
                    for table in tables if isinstance(tables, list) else []:
                        if isinstance(table, dict):
                            datasets.append(
                                {
                                    "tableName": table.get("full_name"),
                                    "name": table.get("description") or table.get("full_name"),
                                }
                            )
                elif tool == "get_schema" and result.get("found"):
                    datasets.append(
                        {
                            "tableName": result.get("table"),
                            "name": result.get("description") or result.get("table"),
                        }
                    )
                    source_warnings = result.get("warnings", [])
                    for warning in source_warnings if isinstance(source_warnings, list) else []:
                        warnings.append(str(warning))
            continue

        # Deliberately drop thinking and intermediate model text events.

    if not final_text.strip():
        raise HarnessRunError("dsh completed without a final assistant answer")

    if sql is None and last_compiled_sql:
        sql = last_compiled_sql
        sql_source_call_id = last_compile_call_id
        validation = None
        validation_call_id = None

    answer = _presentation_answer(final_text)
    if not answer:
        answer = "已完成分析。请查看下方指标、资产、SQL 与校验结果。"

    return {
        "sessionId": session_id,
        "answer": answer,
        "summary": _answer_summary(answer),
        "stopReason": stop_reason,
        "events": events,
        "sql": sql,
        "validation": validation,
        "validationState": _validation_state(sql, validation),
        "sqlSourceCallId": sql_source_call_id,
        "validationCallId": validation_call_id,
        "clarification": clarification,
        "researchPolicy": research_policy,
        "semanticPlan": semantic_plan,
        "semanticValidation": semantic_validation,
        "evidence": {
            "metrics": _dedupe_dicts(metrics, "code"),
            "assets": _dedupe_dicts(assets, "assetId"),
            "datasets": _dedupe_dicts(datasets, "tableName"),
            "codeValues": code_values,
            "dimensions": list(dict.fromkeys(dimensions)),
            "period": period,
            "caliber": caliber,
            "warnings": list(dict.fromkeys(warnings)),
        },
        "sqlExecuted": False,
        "hiddenReasoningExposed": False,
    }


class HeadlessHarnessRunner:
    def __init__(self, *, timeout_seconds: float | None = None, model_mode: str | None = None,
                 task_tier: str = "standard") -> None:
        self.repo_root = Path(__file__).resolve().parents[3]
        self.agent_root = self.repo_root / "agent"
        if task_tier not in ("standard", "multi"):
            raise ValueError("Unknown Agent task tier")
        self.task_tier = task_tier
        self.timeout_seconds = timeout_seconds or float(
            os.getenv("DATACONTROL_AGENT_RUN_TIMEOUT_MULTI" if task_tier == "multi"
                      else "DATACONTROL_AGENT_RUN_TIMEOUT",
                      "600" if task_tier == "multi" else "120")
        )
        self.dsh_home = Path(
            os.getenv("DSH_HOME", str(self.repo_root / ".local" / "dsh-home-v0.2.1-rc.3"))
        ).resolve()
        suffix = "dsh.cmd" if os.name == "nt" else "dsh"
        self.dsh_bin = self.agent_root / "dsh" / "node_modules" / ".bin" / suffix
        self.dsh_js_entry = (
            self.agent_root / "dsh" / "node_modules" / "@deepseek-ai" / "dsh" / "lib" / "bin.js"
        )
        # An explicit request choice always wins over legacy process-level settings.
        self.model_mode = model_mode if model_mode is not None else os.getenv(
            "DATACONTROL_AGENT_MODEL_MODE", "deepseek"
        )
        if self.model_mode not in ("deepseek", "free-test"):
            raise ValueError("Unsupported DataAgent model mode")
        self.free_test = self.model_mode == "free-test"
        self.profile = (
            "dataagent-headless-free" if self.free_test
            else ("dataagent-headless-multi" if task_tier == "multi"
                  else os.getenv("DATACONTROL_DSH_PROFILE", "dataagent-headless"))
        )

    @property
    def profile_dir(self) -> Path:
        return self.dsh_home / "profiles" / self.profile

    async def _mcp_reachable(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=1.0, trust_env=False) as client:
                await client.get("http://127.0.0.1:8900/mcp")
            return True
        except httpx.HTTPError:
            return False

    async def health(self) -> dict[str, Any]:
        dsh_installed = (self.dsh_js_entry if os.name == "nt" else self.dsh_bin).exists()
        profile_package_ready = (self.profile_dir / "package.json").exists()
        source_overlay = (self.agent_root / "dsh" / "profile" /
                          ("headless-multi.patch.yml" if self.task_tier == "multi"
                           else "headless.patch.yml"))
        active_overlay = self.profile_dir / "cordis.patch.yml"
        provider = "our-free-model" if self.free_test else "deepseek-official"
        model = "kilo-auto/free" if self.free_test else "deepseek-flash"
        try:
            expected = source_overlay.read_bytes()
            if self.free_test:
                expected = expected.replace(
                    b"provider: deepseek-official\n    model: deepseek-flash",
                    b"provider: our-free-model\n    model: kilo-auto/free",
                ).replace(
                    b"provider: deepseek-official\r\n    model: deepseek-flash",
                    b"provider: our-free-model\r\n    model: kilo-auto/free",
                )
            patch_ok = active_overlay.is_file() and active_overlay.read_bytes() == expected
        except OSError:
            patch_ok = False
        plugin_ok = True
        if self.free_test:
            try:
                pkg = json.loads((self.profile_dir / "package.json").read_text(encoding="utf-8"))
                plugin = json.loads((self.profile_dir / "node_modules" / "dsh-our-free-model" / "package.json").read_text(encoding="utf-8"))
                plugin_ok = (
                    (self.repo_root / ".local" / "free-model-test-v2.7.2.ready").is_file()
                    and plugin.get("version") == "2.7.2"
                    and "dsh-our-free-model" in pkg.get("dsh", {}).get("profile", {}).get("bundles", [])
                )
            except (OSError, ValueError, AttributeError):
                plugin_ok = False
        profile_ready = profile_package_ready and patch_ok and plugin_ok
        api_key_present = bool(os.getenv("DEEPSEEK_API_KEY"))
        # Public gateway consent belongs to each request, not the server process.
        # This health check reports whether the optional profile is installed.
        key_ready = self.free_test or api_key_present
        mcp_reachable = await self._mcp_reachable()
        ready = dsh_installed and profile_ready and key_ready and mcp_reachable
        blockers: list[str] = []
        if not dsh_installed:
            blockers.append("DeepSeek Harness is not installed")
        if not profile_ready:
            blockers.append(
                "Free model test profile missing; run the optional scripts/setup-free-model-test installer"
                if self.free_test else "DataAgent profile is missing/outdated: rerun setup-agent"
            )
        if not key_ready:
            blockers.append("DEEPSEEK_API_KEY is not set")
        if not mcp_reachable:
            blockers.append("Agent3 MCP is not reachable on 127.0.0.1:8900")
        return {
            "ready": ready, "dshInstalled": dsh_installed,
            "profileReady": profile_ready, "apiKeyPresent": api_key_present,
            "apiKeyRequired": not self.free_test, "mcpReachable": mcp_reachable,
            "profile": self.profile, "modelMode": "free-test" if self.free_test else "deepseek",
            "provider": provider, "model": model,
            "reason": "; ".join(blockers) if blockers else None,
        }

    def _command(self, session_id: str | None) -> list[str]:
        if os.name == "nt":
            # Launch the actual pinned JS entrypoint, not npm's .cmd wrapper.
            # This preserves Unicode checkout paths and avoids cmd.exe quoting.
            command = ["node", str(self.dsh_js_entry), "--profile", self.profile, "--json"]
        else:
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
            "limit": 8 * 1024 * 1024,
        }
        # Argument-vector execution is safe for CJK/space-containing Windows
        # paths because the Windows command begins with node.exe, not a .cmd file.
        return await asyncio.create_subprocess_exec(*command, **process_kwargs)

    async def _capture_trace(
        self, stream: asyncio.StreamReader, request_id: str,
        on_activity: Callable[[dict[str, Any]], None] | None = None,
    ) -> str:
        """Collect complete JSONL for the existing parser while reporting safe live events."""
        lines: list[str] = []
        tool_labels: dict[str, str] = {}
        debug_payloads_enabled = os.getenv("DATACONTROL_ADMIN_WORKBENCH_ENABLED") == "1"
        safe_native = {"todo_write", "goal", "subagent", "subagent_fork", "workflow"}
        while True:
            raw = await stream.readline()
            if not raw:
                break
            line = raw.decode("utf-8", errors="replace")
            lines.append(line)
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(event, dict):
                continue
            event_type = event.get("type")
            # Capture tool payloads for the authenticated Portal trace store only.
            # The Portal strips inputs/outputs before forwarding events to normal browsers.
            # Hidden reasoning events are deliberately never captured.
            if event_type == "tool_call":
                tool_name = str(event.get("tool") or "")
                suffix = _tool_suffix(tool_name)
                tool = suffix if suffix in MCP_TOOL_SUFFIXES or suffix in safe_native else "harness_tool"
                call_id = event.get("callId")
                if isinstance(call_id, str):
                    tool_labels[call_id] = tool
                LOGGER.info("[Agent:%s] TOOL_START %s", request_id, tool)
                if on_activity and ((tool_name.startswith("mcp__agent3__") and suffix in MCP_TOOL_SUFFIXES)
                                    or suffix in safe_native):
                    if isinstance(call_id, str) and re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", call_id):
                        activity: dict[str, Any] = {"type": "tool_call", "callId": call_id, "tool": suffix}
                        if debug_payloads_enabled:
                            activity["input"] = event.get("input") if isinstance(event.get("input"), dict) else {}
                        on_activity(activity)
            elif event_type == "tool_result":
                call_id = event.get("callId")
                tool = tool_labels.get(call_id, "harness_tool") if isinstance(call_id, str) else "harness_tool"
                raw_status = event.get("status")
                status = raw_status if raw_status in {"completed", "error", "failed", "success"} else "unknown"
                LOGGER.info("[Agent:%s] TOOL_END %s status=%s", request_id, tool, status)
                if on_activity and (tool in MCP_TOOL_SUFFIXES or tool in safe_native):
                    if isinstance(call_id, str) and re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", call_id):
                        activity: dict[str, Any] = {"type": "tool_result", "callId": call_id, "tool": tool, "status": status}
                        if debug_payloads_enabled:
                            activity["output"] = _json_or_text(event.get("result"))
                        on_activity(activity)
        return "".join(lines)

    async def run(
        self, question: str, *, session_id: str | None = None,
        on_activity: Callable[[dict[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        if not question.strip():
            raise HarnessRunError("DataAgent question cannot be empty")

        health = await self.health()
        if not health["ready"]:
            raise HarnessRunError(str(health["reason"] or "DataAgent runtime is not ready"))

        env = _with_loopback_no_proxy(os.environ.copy())
        env["DSH_HOME"] = str(self.dsh_home)
        env["DSH_TELEMETRY_MODE"] = "DISABLED"
        request_id = uuid.uuid4().hex[:8]
        started = time.monotonic()
        LOGGER.info("[Agent:%s] START session=%s", request_id, "resume" if session_id else "new")
        if self.free_test:
            if session_id and not session_id.startswith("free-test:"):
                raise HarnessRunError("Start a new conversation for public free-test mode")
            native_session_id = session_id[len("free-test:"):] if session_id else None
        else:
            if session_id and session_id.startswith("free-test:"):
                raise HarnessRunError("Start a new conversation for the official DeepSeek model")
            native_session_id = session_id
        process = await self._spawn(self._command(native_session_id), env)
        try:
            assert process.stdin is not None
            assert process.stdout is not None
            assert process.stderr is not None
            process.stdin.write(question.encode("utf-8"))
            await process.stdin.drain()
            process.stdin.close()

            stdout_text, stderr, _ = await asyncio.wait_for(
                asyncio.gather(
                    self._capture_trace(process.stdout, request_id, on_activity),
                    process.stderr.read(),
                    process.wait(),
                ),
                timeout=self.timeout_seconds,
            )
        except asyncio.CancelledError:
            # Stop the actual Harness process, not just the browser spinner.
            if process.returncode is None:
                process.kill()
                await process.wait()
            LOGGER.info("[Agent:%s] CANCELLED elapsed=%.1fs", request_id, time.monotonic() - started)
            raise
        except TimeoutError as exc:
            if process.returncode is None:
                process.kill()
                await process.wait()
            LOGGER.warning("[Agent:%s] TIMEOUT elapsed=%.1fs", request_id, time.monotonic() - started)
            raise HarnessRunError(
                f"dsh request exceeded {self.timeout_seconds:g}s timeout"
            ) from exc

        stderr_text = stderr.decode("utf-8", errors="replace")
        if process.returncode != 0:
            LOGGER.error("[Agent:%s] ERROR exit_code=%d elapsed=%.1fs", request_id, process.returncode, time.monotonic() - started)
            detail = stderr_text.strip()[-1600:] or "dsh exited without diagnostics"
            raise HarnessRunError(f"dsh exited with code {process.returncode}: {detail}")
        try:
            result = parse_event_stream(stdout_text)
        except HarnessRunError:
            LOGGER.error("[Agent:%s] ERROR missing_final_answer elapsed=%.1fs", request_id, time.monotonic() - started)
            raise
        LOGGER.info(
            "[Agent:%s] DONE elapsed=%.1fs tools=%d sql=%s validation=%s",
            request_id,
            time.monotonic() - started,
            sum(1 for event in result["events"] if event["type"] == "tool_call"),
            "yes" if result["sql"] else "no",
            result["validationState"],
        )
        if self.free_test and result.get("sessionId"):
            result["sessionId"] = "free-test:" + result["sessionId"]
        result["durationMs"] = int((time.monotonic() - started) * 1000)
        result["toolCallCount"] = sum(
            1 for event in result["events"] if event["type"] == "tool_call"
        )
        return result
