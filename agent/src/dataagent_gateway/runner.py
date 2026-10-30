from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import time
import uuid
from pathlib import Path
from typing import Any, Callable

import httpx

from dataagent_gateway.local_provider import (
    LocalModelError, discover_local_model, expected_overlay, profile_name,
)


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



def _debug_capture_enabled() -> bool:
    return os.getenv("DATACONTROL_AGENT_DEBUG_CAPTURE", "1").strip().lower() not in {"0", "false", "off", "no"}


def _redact_config_text(text: str) -> str:
    text = re.sub(
        r"(?im)^(\s*(?:api[_-]?key|password|secret|credential|access[_-]?token|authorization|token|refresh[_-]?token)\s*:\s*).+$",
        r"\1[REDACTED]", text,
    )
    return re.sub(r"(?i)(Bearer\s+)[A-Za-z0-9._~+/-]+=*", r"\1[REDACTED]", text)

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
        selected_mode = model_mode if model_mode is not None else os.getenv(
            "DATACONTROL_AGENT_MODEL_MODE", "deepseek"
        )
        if selected_mode not in ("deepseek", "free-test", "local-deepseek"):
            raise ValueError("Unsupported DataAgent model mode")
        self.model_mode = selected_mode
        self.free_test = self.model_mode == "free-test"
        self.local_model = self.model_mode == "local-deepseek"
        timeout_variable = ("DATACONTROL_AGENT_RUN_TIMEOUT_LOCAL" if self.local_model
                            else "DATACONTROL_AGENT_RUN_TIMEOUT_MULTI" if task_tier == "multi"
                            else "DATACONTROL_AGENT_RUN_TIMEOUT")
        default_timeout = ("1200" if task_tier == "multi" else "900") if self.local_model else (
            "600" if task_tier == "multi" else "120"
        )
        self.timeout_seconds = timeout_seconds or float(os.getenv(timeout_variable, default_timeout))
        self.dsh_home = Path(
            os.getenv("DSH_HOME", str(self.repo_root / ".local" / "dsh-home-v0.2.1-rc.3"))
        ).resolve()
        suffix = "dsh.cmd" if os.name == "nt" else "dsh"
        self.dsh_bin = self.agent_root / "dsh" / "node_modules" / ".bin" / suffix
        self.dsh_js_entry = (
            self.agent_root / "dsh" / "node_modules" / "@deepseek-ai" / "dsh" / "lib" / "bin.js"
        )
        self.profile = (
            profile_name(task_tier) if self.local_model
            else "dataagent-headless-free" if self.free_test
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
        provider = "local-llama" if self.local_model else "our-free-model" if self.free_test else "deepseek-official"
        model = "unknown" if self.local_model else "kilo-auto/free" if self.free_test else "deepseek-flash"
        local = None
        local_error = None
        if self.local_model:
            try:
                local = await asyncio.to_thread(discover_local_model)
                model = local.id
            except LocalModelError as exc:
                local_error = str(exc)
        try:
            expected = source_overlay.read_bytes()
            if self.local_model and local:
                expected = expected_overlay(self.task_tier, local).encode("utf-8")
            if self.free_test:
                expected = expected.replace(
                    b"provider: deepseek-official\n    model: deepseek-flash",
                    b"provider: our-free-model\n    model: kilo-auto/free",
                ).replace(
                    b"provider: deepseek-official\r\n    model: deepseek-flash",
                    b"provider: our-free-model\r\n    model: kilo-auto/free",
                )
            patch_ok = active_overlay.is_file() and active_overlay.read_bytes() == expected
        except (OSError, LocalModelError):
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
        # Neither public-test nor local llama.cpp requires a DeepSeek API key.
        key_ready = self.free_test or self.local_model or api_key_present
        mcp_reachable = await self._mcp_reachable()
        ready = dsh_installed and profile_ready and key_ready and mcp_reachable and (
            not self.local_model or local is not None
        )
        blockers: list[str] = []
        if not dsh_installed:
            blockers.append("DeepSeek Harness is not installed")
        if not profile_ready:
            blockers.append(
                "Local dsh profile missing or stale; run .\\scripts\\setup-local-model.ps1"
                if self.local_model else
                "Free model test profile missing; run the optional scripts/setup-free-model-test installer"
                if self.free_test else "DataAgent profile is missing/outdated: rerun setup-agent"
            )
        if local_error:
            blockers.append(local_error)
        if not key_ready:
            blockers.append("DEEPSEEK_API_KEY is not set")
        if not mcp_reachable:
            blockers.append("Agent3 MCP is not reachable on 127.0.0.1:8900")
        return {
            "ready": ready, "dshInstalled": dsh_installed,
            "profileReady": profile_ready, "apiKeyPresent": api_key_present,
            "apiKeyRequired": not (self.free_test or self.local_model), "mcpReachable": mcp_reachable,
            "profile": self.profile, "modelMode": self.model_mode,
            "provider": provider, "model": model,
            "reason": "; ".join(blockers) if blockers else None,
        }

    def debug_config(self) -> dict[str, Any]:
        """Expose effective development configuration without revealing secret values."""
        root = self.repo_root
        specs: list[tuple[str, str, str, bool]] = [
            ("agent/dsh/profile/headless.patch.yml", "profile-source", "标准任务 Profile 源配置", self.task_tier == "standard"),
            ("agent/dsh/profile/headless-multi.patch.yml", "profile-source", "多步任务 Profile 源配置", self.task_tier == "multi"),
            ("agent/src/dataagent_gateway/local_provider.py", "provider-source", "本地模型发现和 Profile 配置", self.local_model),
            ("agent/dsh/profile/cordis.patch.yml", "profile-template", "仓库内 Profile 模板", False),
            ("agent/dsh/profile/pinned-plugin-ids.json", "plugin-lock", "固定插件清单", True),
            ("agent/tool-catalog.json", "tool-catalog", "Agent3 MCP 工具白名单", True),
            ("agent/guard-plugin/src/policy.ts", "guard-policy", "Guard 确定性策略源码", True),
            ("agent/guard-plugin/src/index.ts", "guard-integration", "Guard 插件接入源码", True),
            ("agent/guard-plugin/dist/index.js", "guard-runtime", "Guard 实际加载的构建产物", True),
            ("agent/src/agent3/services/core.py", "hard-policy", "Agent3 服务端确定性约束", True),
            ("agent/src/agent3/services/development.py", "hard-policy", "DDL/ETL 草案与人工审查约束", True),
            ("agent/src/agent3/semantic/validator.py", "hard-policy", "语义计划校验实现", True),
            ("agent/src/agent3/sql/validation/validator.py", "hard-policy", "SQL 校验与风险规则", True),
            ("agent/src/agent3/policy/row_filter.py", "hard-policy", "数据访问过滤策略", True),
            ("backend/app/api/agent.py", "hard-policy", "Portal 结果安全与执行边界", True),
        ]
        active_overlay = self.profile_dir / "cordis.patch.yml"
        active_package = self.profile_dir / "package.json"
        for label, path in (
            ("当前实际加载的 Profile 配置", active_overlay),
            ("当前 Profile 安装包清单", active_package),
        ):
            specs.append((str(path), "active-runtime", label, True))
        skill_root = root / "agent" / ".dsh" / "skills"
        if skill_root.exists():
            for path in sorted(skill_root.glob("*/SKILL.md")):
                specs.append((str(path), "skill", "Skill: " + path.parent.name, True))

        files: list[dict[str, Any]] = []
        for raw_path, kind, label, active in specs:
            path = Path(raw_path)
            if not path.is_absolute():
                path = root / path
            try:
                raw = path.read_bytes()
                text = raw.decode("utf-8", errors="replace")
                files.append({
                    "id": label + ":" + raw_path,
                    "label": label,
                    "kind": kind,
                    "path": raw_path if not Path(raw_path).is_absolute() else "DSH_HOME/profiles/" + self.profile + "/" + path.name,
                    "exists": True,
                    "activeForRequest": active and (kind != "active-runtime" or path.exists()),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "bytes": len(raw),
                    "content": _redact_config_text(text)[:500_000],
                    "truncated": len(text) > 500_000,
                })
            except OSError:
                files.append({
                    "id": label + ":" + raw_path,
                    "label": label,
                    "kind": kind,
                    "path": raw_path,
                    "exists": False,
                    "activeForRequest": False,
                    "sha256": None,
                    "bytes": 0,
                    "content": "",
                    "truncated": False,
                })

        local_id = None
        if self.local_model:
            try:
                local_id = discover_local_model(timeout=2.0).id
            except LocalModelError:
                local_id = "unavailable"
        return {
            "captureEnabled": _debug_capture_enabled(),
            "modelMode": self.model_mode,
            "taskTier": self.task_tier,
            "profile": self.profile,
            "profileDir": "DSH_HOME/profiles/" + self.profile,
            "provider": "local-llama" if self.local_model else "our-free-model" if self.free_test else "deepseek-official",
            "model": local_id if self.local_model else "kilo-auto/free" if self.free_test else "deepseek-flash",
            "timeoutSeconds": self.timeout_seconds,
            "apiKeyPresent": bool(os.getenv("DEEPSEEK_API_KEY")),
            "sqlExecutionEnabled": False,
            "hiddenReasoningCaptured": False,
            "files": files,
            "limitations": [
                "仅展示 Harness 实际输出的 JSONL 事件；未由 Harness 输出的底层 HTTP 请求体、Token 用量等不会被伪造。",
                "隐藏思维链不采集；可审计的工具调用、工具结果、状态、最终答复与配置原文会尽可能保留。",
                "源配置与实际加载的 DSH_HOME Profile 分开显示，文件哈希用于识别版本差异。",
            ],
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
        trace_started = time.monotonic()
        tool_labels: dict[str, str] = {}
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
                if on_activity and _debug_capture_enabled() and line.strip():
                    on_activity({
                        "type": "debug_event", "source": "dsh_stdout",
                        "eventType": "unparsed_stdout",
                        "payload": {"elapsedMs": int((time.monotonic() - trace_started) * 1000),
                                    "text": line.rstrip("\r\n")},
                    })
                continue
            if not isinstance(event, dict):
                continue
            event_type = event.get("type")
            if on_activity and _debug_capture_enabled():
                private_types = {"thinking", "reasoning", "chain_of_thought", "cot", "analysis"}
                channel = str(event.get("channel") or event.get("kind") or "").lower()
                role = str(event.get("role") or "").lower()
                is_private = str(event_type or "").lower() in private_types or channel in private_types
                is_intermediate_assistant_text = (
                    role == "assistant"
                    and str(event_type or "").lower() in {"message", "assistant_message", "model_output", "text_delta"}
                    and channel not in {"final", "answer"}
                )
                if is_private or is_intermediate_assistant_text:
                    payload = {
                        "type": event_type, "channel": channel or None, "role": role or None,
                        "contentCaptured": False,
                        "note": "private reasoning or intermediate assistant text is not captured",
                    }
                elif event_type == "session":
                    payload = {"type": "session", "sessionId": "[SERVER-OWNED]"}
                else:
                    payload = event
                on_activity({
                    "type": "debug_event", "source": "dsh_jsonl",
                    "eventType": str(event_type or "unknown"),
                    "payload": {"elapsedMs": int((time.monotonic() - trace_started) * 1000),
                                "event": payload},
                })
            # Never stream user questions, raw tool payloads, SQL, or hidden reasoning.
            # Only known Agent3 tool identities and validated statuses are UI activity.
            if event_type == "tool_call":
                tool_name = str(event.get("tool") or "")
                suffix = _tool_suffix(tool_name)
                tool = suffix if suffix in MCP_TOOL_SUFFIXES or suffix in safe_native else "harness_tool"
                call_id = event.get("callId")
                if isinstance(call_id, str):
                    tool_labels[call_id] = tool
                LOGGER.info("[Agent:%s] TOOL_START %s", request_id, tool)
                if on_activity and tool_name.startswith("mcp__agent3__") and suffix in MCP_TOOL_SUFFIXES:
                    if isinstance(call_id, str) and re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", call_id):
                        on_activity({"type": "tool_call", "callId": call_id, "tool": suffix})
            elif event_type == "tool_result":
                call_id = event.get("callId")
                tool = tool_labels.get(call_id, "harness_tool") if isinstance(call_id, str) else "harness_tool"
                raw_status = event.get("status")
                status = raw_status if raw_status in {"completed", "error", "failed", "success"} else "unknown"
                LOGGER.info("[Agent:%s] TOOL_END %s status=%s", request_id, tool, status)
                if on_activity and tool in MCP_TOOL_SUFFIXES:
                    if isinstance(call_id, str) and re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", call_id):
                        on_activity({"type": "tool_result", "callId": call_id, "tool": tool, "status": status})
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
        if self.local_model:
            env["DATACONTROL_LOCAL_MODEL_API_KEY"] = "local-no-key-required"
        request_id = uuid.uuid4().hex[:8]
        started = time.monotonic()
        if on_activity and _debug_capture_enabled():
            current_config = self.debug_config()
            snapshot_files = [
                {
                    key: item[key]
                    for key in ("label", "kind", "path", "exists", "activeForRequest", "sha256", "content", "truncated")
                    if key in item
                }
                for item in current_config["files"]
                if item.get("activeForRequest") or item.get("kind") in {"guard-policy", "guard-integration", "tool-catalog", "skill"}
            ]
            on_activity({
                "type": "debug_event", "source": "gateway", "eventType": "run_start",
                "payload": {
                    "requestId": request_id, "modelMode": self.model_mode,
                    "taskTier": self.task_tier, "profile": self.profile,
                    "provider": current_config["provider"],
                    "model": current_config["model"],
                    "timeoutSeconds": self.timeout_seconds, "sessionResumed": bool(session_id),
                    "questionSentToHarness": question,
                    "effectiveConfigSnapshot": {
                        "profile": current_config["profile"],
                        "provider": current_config["provider"],
                        "model": current_config["model"],
                        "captureEnabled": current_config["captureEnabled"],
                        "files": snapshot_files,
                    },
                    "note": "该问题文本通过 stdin 发送给 dsh；底层 Provider HTTP 请求体由 Harness 管理。",
                },
            })
        LOGGER.info("[Agent:%s] START session=%s", request_id, "resume" if session_id else "new")
        local_identity = None
        if self.local_model:
            try:
                local_identity = discover_local_model(timeout=4.0).identity
            except LocalModelError as exc:
                raise HarnessRunError(str(exc)) from exc
            prefix = "local-deepseek:" + local_identity + ":"
            if session_id and not session_id.startswith(prefix):
                raise HarnessRunError("Local model changed; start a new conversation")
            native_session_id = session_id[len(prefix):] if session_id else None
        elif self.free_test:
            if session_id and not session_id.startswith("free-test:"):
                raise HarnessRunError("Start a new conversation for public free-test mode")
            native_session_id = session_id[len("free-test:"):] if session_id else None
        else:
            if session_id and (session_id.startswith("free-test:") or session_id.startswith("local-deepseek:")):
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
        if on_activity and _debug_capture_enabled() and stderr_text.strip():
            on_activity({
                "type": "debug_event", "source": "dsh_stderr", "eventType": "stderr",
                "payload": {"text": stderr_text[-64_000:]},
            })
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
        if self.local_model and result.get("sessionId"):
            result["sessionId"] = "local-deepseek:" + str(local_identity) + ":" + result["sessionId"]
        result["durationMs"] = int((time.monotonic() - started) * 1000)
        result["toolCallCount"] = sum(
            1 for event in result["events"] if event["type"] == "tool_call"
        )
        return result
