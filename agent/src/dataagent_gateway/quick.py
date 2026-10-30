"""Single-request local answer mode; deliberately NOT a trusted Agent workflow.

The full Agent path still uses dsh + Agent3 MCP. This path reduces CPU latency by
skipping tool orchestration, requesting zero reasoning tokens and bounding output.
"""
from __future__ import annotations

import asyncio
import re
import time
from collections.abc import Callable
from typing import Any

import httpx

from dataagent_gateway.local_provider import LocalModelError, discover_local_model
from dataagent_gateway.runner import HarnessRunError, _debug_capture_enabled

QUICK_TOKEN_LIMITS = (128, 256, 512)
QUICK_TIMEOUT_SECONDS = 240.0
QUICK_NOTICE = "**极速回答（未检索元数据、未校验 SQL）**"
QUICK_SYSTEM = (
    "你是 DataControl 本地极速回答助手。请直接用简洁的中文回答，不输出思考过程。"
    "这是单次文本生成，不具备 MCP、数据库、文件或互联网工具访问能力。"
    "不能声称已查询元数据、已验证统计口径或 SQL。"
    "如果用户需要真实数据集字段、指标口径、可信 SQL 或具体数值，"
    "明确建议切换标准问数模式，不要编造。"
)


def _clean_answer(value: str) -> str:
    # Many reasoning-model templates separate reasoning_content, while some may
    # emit thinking tags in content. Never expose those tags to normal chat.
    cleaned = re.sub(r"<think>.*?</think>", "", value, flags=re.DOTALL | re.IGNORECASE).strip()
    if re.search(r"</?think>", cleaned, flags=re.IGNORECASE):
        return ""
    return cleaned


class LocalQuickRunner:
    """Fast local-only model completion, without Agent claims or tool access."""

    def __init__(self, max_tokens: int = 256) -> None:
        if max_tokens not in QUICK_TOKEN_LIMITS:
            raise ValueError("Unsupported quick answer token limit")
        self.max_tokens = max_tokens

    async def health(self) -> dict[str, Any]:
        try:
            model = await asyncio.to_thread(discover_local_model, timeout=3.0)
            reason = None
        except LocalModelError as exc:
            model = None
            reason = str(exc)
        return {
            "ready": model is not None,
            "modelMode": "local-deepseek",
            "provider": "local-llama",
            "model": model.id if model else "unavailable",
            "profile": "local-quick-direct",
            "reason": reason,
            "apiKeyRequired": False,
            "apiKeyPresent": False,
            "mcpReachable": False,
            "quickMode": True,
            "toolExecutionEnabled": False,
            "sqlExecutionEnabled": False,
            "reasoningBudgetRequested": 0,
        }

    async def run(
        self,
        question: str,
        *,
        session_id: str | None = None,
        on_activity: Callable[[dict[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        if session_id:
            raise HarnessRunError("Fast local mode is stateless; start a new quick conversation")
        if not question.strip():
            raise HarnessRunError("Quick question cannot be empty")
        try:
            model = await asyncio.to_thread(discover_local_model, timeout=4.0)
        except LocalModelError as exc:
            raise HarnessRunError(str(exc)) from exc
        started = time.monotonic()
        if on_activity and _debug_capture_enabled():
            on_activity({
                "type": "debug_event",
                "source": "local-quick",
                "eventType": "run_start",
                "payload": {
                    "modelMode": "local-deepseek",
                    "taskTier": "quick",
                    "model": model.id,
                    "provider": "local-llama",
                    "profile": "local-quick-direct",
                    "maxTokens": self.max_tokens,
                    "reasoningBudgetRequested": 0,
                    "toolsEnabled": False,
                    "questionSentToModel": question,
                },
            })
        payload = {
            "model": model.id,
            "stream": False,
            "temperature": 0.2,
            "max_tokens": self.max_tokens,
            # llama.cpp accepts a per-request budget when its server launch
            # did not force a global budget; older builds may ignore this.
            "thinking_budget_tokens": 0,
            "messages": [
                {"role": "system", "content": QUICK_SYSTEM},
                {"role": "user", "content": question},
            ],
        }
        try:
            async with httpx.AsyncClient(
                trust_env=False, timeout=httpx.Timeout(
                    QUICK_TIMEOUT_SECONDS, connect=5.0, read=QUICK_TIMEOUT_SECONDS,
                ),
            ) as client:
                response = await client.post(model.base_url + "/chat/completions", json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.TimeoutException as exc:
            raise HarnessRunError(f"Local quick response exceeded {QUICK_TIMEOUT_SECONDS:g}s timeout") from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise HarnessRunError(f"Local quick model request failed ({type(exc).__name__}); check llama.cpp logs") from exc
        choices = data.get("choices") if isinstance(data, dict) else None
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
            raise HarnessRunError("Local quick model returned no completion choice")
        message = choices[0].get("message")
        answer = _clean_answer(str(message.get("content") or "")) if isinstance(message, dict) else ""
        if not answer:
            raise HarnessRunError(
                "Local model returned only reasoning or an empty response. "
                "Check llama.cpp reasoning support and try 256/512 output tokens."
            )
        elapsed = int((time.monotonic() - started) * 1000)
        if on_activity and _debug_capture_enabled():
            usage = data.get("usage") if isinstance(data, dict) else None
            on_activity({
                "type": "debug_event",
                "source": "local-quick",
                "eventType": "run_complete",
                "payload": {
                    "durationMs": elapsed,
                    "maxTokens": self.max_tokens,
                    "reasoningBudgetRequested": 0,
                    "usage": usage if isinstance(usage, dict) else None,
                    "answer": answer,
                },
            })
        return {
            "sessionId": None,
            "answer": QUICK_NOTICE + "\n\n" + answer,
            "summary": answer.split("\n", 1)[0][:80],
            "stopReason": str(choices[0].get("finish_reason") or "completed"),
            "events": [],
            "sql": None,
            "validation": None,
            "validationState": "not_applicable",
            "sqlExecuted": False,
            "hiddenReasoningExposed": False,
            "durationMs": elapsed,
            "toolCallCount": 0,
        }
