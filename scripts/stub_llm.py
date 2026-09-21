"""Deterministic DeepSeek Messages stub for DataControl harness acceptance.

Derived from the scripted stub used during the P3 handoff. It deliberately drives
one governed path: resolve_metric -> compile_query -> validate_sql -> final answer.
This lets CI exercise Portal -> Gateway -> dsh -> MCP -> Agent3 without a real API key.
"""
from __future__ import annotations

import json
import os
import re
import uuid
from pathlib import Path
from typing import Any, Iterator

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

LOG = Path(os.getenv("DATACONTROL_STUB_LOG", ".local/stub_requests.jsonl"))
app = FastAPI(title="DataControl deterministic LLM stub")


def sse(event: dict[str, Any]) -> str:
    return f"event: {event['type']}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"


def text_of(block: Any) -> str:
    if isinstance(block, str):
        return block
    if isinstance(block, dict):
        if block.get("type") == "text":
            return str(block.get("text", ""))
        if block.get("type") == "tool_result":
            content = block.get("content")
            if isinstance(content, str):
                return content
            return "".join(text_of(item) for item in (content or []))
    if isinstance(block, list):
        return "".join(text_of(item) for item in block)
    return ""


def tool_name(tools: list[dict[str, Any]], suffix: str) -> str:
    name = next(
        (str(tool["name"]) for tool in tools if str(tool.get("name", "")).endswith(suffix)),
        None,
    )
    if not name:
        raise RuntimeError(f"required tool is missing from dsh request: {suffix}")
    return name


def stream_tool(name: str, args: dict[str, Any]) -> Iterator[str]:
    message_id = f"msg_{uuid.uuid4().hex[:12]}"
    tool_id = f"toolu_{uuid.uuid4().hex[:12]}"
    yield sse(
        {
            "type": "message_start",
            "message": {
                "id": message_id,
                "type": "message",
                "role": "assistant",
                "content": [],
                "model": "datacontrol-stub",
                "usage": {"input_tokens": 10, "output_tokens": 0},
            },
        }
    )
    yield sse(
        {
            "type": "content_block_start",
            "index": 0,
            "content_block": {
                "type": "tool_use",
                "id": tool_id,
                "name": name,
                "input": {},
            },
        }
    )
    yield sse(
        {
            "type": "content_block_delta",
            "index": 0,
            "delta": {
                "type": "input_json_delta",
                "partial_json": json.dumps(args, ensure_ascii=False),
            },
        }
    )
    yield sse({"type": "content_block_stop", "index": 0})
    yield sse(
        {
            "type": "message_delta",
            "delta": {"stop_reason": "tool_use"},
            "usage": {"output_tokens": 20},
        }
    )
    yield sse({"type": "message_stop"})


def stream_text(text: str) -> Iterator[str]:
    message_id = f"msg_{uuid.uuid4().hex[:12]}"
    yield sse(
        {
            "type": "message_start",
            "message": {
                "id": message_id,
                "type": "message",
                "role": "assistant",
                "content": [],
                "model": "datacontrol-stub",
                "usage": {"input_tokens": 10, "output_tokens": 0},
            },
        }
    )
    yield sse(
        {
            "type": "content_block_start",
            "index": 0,
            "content_block": {"type": "text", "text": ""},
        }
    )
    yield sse(
        {
            "type": "content_block_delta",
            "index": 0,
            "delta": {"type": "text_delta", "text": text},
        }
    )
    yield sse({"type": "content_block_stop", "index": 0})
    yield sse(
        {
            "type": "message_delta",
            "delta": {"stop_reason": "end_turn"},
            "usage": {"output_tokens": 30},
        }
    )
    yield sse({"type": "message_stop"})


def _content_blocks(message: dict[str, Any]) -> list[dict[str, Any]]:
    content = message.get("content")
    return content if isinstance(content, list) else []


@app.post("/v1/messages")
async def messages(request: Request):
    body = await request.json()
    tools = body.get("tools") or []
    messages_list = body.get("messages") or []

    # Non-agent calls such as session-title generation get a short deterministic answer.
    if not tools:
        return StreamingResponse(
            stream_text("贷款余额查询"),
            media_type="text/event-stream",
        )

    last_user_index = max(
        (
            index
            for index, message in enumerate(messages_list)
            if message.get("role") == "user"
            and any(block.get("type") == "text" for block in _content_blocks(message))
        ),
        default=0,
    )
    turn = messages_list[last_user_index:]
    calls: list[tuple[str, dict[str, Any]]] = []
    results: list[str] = []
    for message in turn:
        for block in _content_blocks(message):
            if block.get("type") == "tool_use":
                calls.append((str(block["name"]), block.get("input") or {}))
            if block.get("type") == "tool_result":
                results.append(text_of(block))

    question = text_of(messages_list[last_user_index].get("content")) if messages_list else ""
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "tools": [tool.get("name") for tool in tools],
                    "n_messages": len(messages_list),
                    "question": question,
                    "system_head": str(body.get("system"))[:300],
                },
                ensure_ascii=False,
            )
            + "\n"
        )

    dimensions = ["region_code"] if re.search(r"地区|region", question) else []
    step = len(calls)
    if step == 0:
        return StreamingResponse(
            stream_tool(tool_name(tools, "resolve_metric"), {"phrase": "本期贷款余额"}),
            media_type="text/event-stream",
        )
    if step == 1:
        metric = json.loads(results[-1]).get("metric") or {}
        return StreamingResponse(
            stream_tool(
                tool_name(tools, "compile_query"),
                {
                    "metric_id": metric.get("id", "metric_loan_balance"),
                    "dimensions": dimensions,
                    "time_values": ["LATEST"],
                },
            ),
            media_type="text/event-stream",
        )
    if step == 2:
        compiled = json.loads(results[-1])
        return StreamingResponse(
            stream_tool(
                tool_name(tools, "validate_sql"),
                {
                    "sql": compiled.get("sql", ""),
                    "metric_id": "metric_loan_balance",
                },
            ),
            media_type="text/event-stream",
        )

    return StreamingResponse(
        stream_text(
            "已基于治理指标各项贷款余额生成可信 SQL，来源表 "
            "stat_prod.dws_loan_region_month，本期解释为最新统计月，SQL 校验通过，未执行。"
        ),
        media_type="text/event-stream",
    )
