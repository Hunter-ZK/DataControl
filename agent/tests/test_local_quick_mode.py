"""One-shot llama.cpp quick-answer mode must never claim Agent evidence."""
import asyncio
import json

import httpx
import pytest

from dataagent_gateway.local_provider import LocalModel
from dataagent_gateway.quick import LocalQuickFailure, LocalQuickRunner, _clean_answer
from dataagent_gateway.runner import HarnessRunError


def test_quick_returns_bounded_text_without_tools(monkeypatch):
    requests = []
    original = httpx.AsyncClient

    async def handler(request):
        requests.append(json.loads(request.content))
        assert request.url.path == "/v1/chat/completions"
        return httpx.Response(200, json={
            "choices": [{
                "finish_reason": "stop",
                "message": {
                    "content": "<think>hidden model working</think>\n可以先这样处理。",
                    "reasoning_content": "private chain",
                },
            }],
            "usage": {"total_tokens": 32},
        })

    def client(*args, **kwargs):
        return original(*args, transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr("dataagent_gateway.quick.httpx.AsyncClient", client)
    monkeypatch.setattr("dataagent_gateway.quick.discover_local_model",
                        lambda **_: LocalModel("actual-model-id", "http://127.0.0.1:9931/v1"))
    monkeypatch.setenv("DATACONTROL_AGENT_DEBUG_CAPTURE", "1")
    activities = []
    result = asyncio.run(LocalQuickRunner(128).run(
        "如何写需求说明？", on_activity=activities.append,
    ))
    assert requests[0]["model"] == "actual-model-id"
    assert requests[0]["thinking_budget_tokens"] == 0
    assert requests[0]["max_tokens"] == 128
    assert requests[0]["stream"] is False
    assert "tools" not in requests[0]
    assert "可以先这样处理" in result["answer"]
    assert "hidden model working" not in result["answer"]
    assert "private chain" not in json.dumps(result)
    assert result["sql"] is None
    assert result["validationState"] == "not_applicable"
    assert result["toolCallCount"] == 0
    assert result["events"] == []
    assert result["sessionId"] is None
    assert result["sqlExecuted"] is False
    assert any(a.get("eventType") == "run_start" for a in activities)




@pytest.mark.parametrize(
    ("model_content", "expected"),
    [
        ("\n</think>\n\n你好！", "你好！"),  # Actual Windows llama.cpp response.
        ("<think>private reasoning</think>\n可以先这样处理。", "可以先这样处理。"),
        ("<think>private reasoning</think>\n</think>\n最终结果", "最终结果"),
        ("没有思考标签的普通回答", "没有思考标签的普通回答"),
        ("<think>unfinished private reasoning", ""),
        ("<think>private reasoning</think>", ""),
        ("</think>", ""),
        ("</think>完成后又开启<think>private unfinished reasoning", ""),
    ],
)
def test_clean_answer_handles_orphan_deepseek_delimiter(model_content, expected):
    assert _clean_answer(model_content) == expected


def test_quick_accepts_exact_llamacpp_orphan_think_response(monkeypatch):
    original_client = httpx.AsyncClient

    def client(*args, **kwargs):
        transport = httpx.MockTransport(lambda _: httpx.Response(
            200, json={
                "choices": [{
                    "finish_reason": "stop",
                    "message": {"content": "\n</think>\n\n你好！"},
                }],
                "usage": {"completion_tokens": 8},
            },
        ))
        return original_client(*args, transport=transport, **kwargs)

    monkeypatch.setattr("dataagent_gateway.quick.httpx.AsyncClient", client)
    monkeypatch.setattr(
        "dataagent_gateway.quick.discover_local_model",
        lambda **_: LocalModel("exact-model", "http://127.0.0.1:9931/v1"),
    )
    result = asyncio.run(LocalQuickRunner(128).run("只回答两个字：你好。"))
    assert result["answer"] == "**极速回答（未检索元数据、未校验 SQL）**\n\n你好！"
    assert result["stopReason"] == "stop"
    assert result["toolCallCount"] == 0


def test_quick_rejects_provider_session_and_invalid_output_limit():
    with pytest.raises(ValueError, match="token limit"):
        LocalQuickRunner(2048)
    with pytest.raises(HarnessRunError, match="stateless"):
        asyncio.run(LocalQuickRunner().run("question", session_id="session-a"))


def test_quick_empty_reasoning_response_is_not_fabricated(monkeypatch):
    original = httpx.AsyncClient
    def client(*args, **kwargs):
        transport = httpx.MockTransport(lambda _: httpx.Response(
            200, json={"choices": [{
                "message": {"content": "", "reasoning_content": "private"},
            }]},
        ))
        return original(*args, transport=transport, **kwargs)

    monkeypatch.setattr("dataagent_gateway.quick.httpx.AsyncClient", client)
    monkeypatch.setattr("dataagent_gateway.quick.discover_local_model",
                        lambda **_: LocalModel("actual-model-id", "http://127.0.0.1:9931/v1"))
    activities = []
    with pytest.raises(LocalQuickFailure) as err:
        asyncio.run(LocalQuickRunner().run("question", on_activity=activities.append))
    assert err.value.code == "LOCAL_EMPTY_ANSWER"
    assert "思考内容" in err.value.user_message
    assert "private" not in err.value.user_message
    assert activities[-1]["eventType"] == "run_failed"
    assert activities[-1]["payload"]["reasoningContentPresent"] is True
    assert "private" not in json.dumps(activities[-1])


def test_gateway_quick_mode_uses_local_runner_only(monkeypatch):
    from dataagent_gateway.app import QueryRequest, health, query
    from fastapi import HTTPException

    monkeypatch.setattr("dataagent_gateway.quick.discover_local_model",
                        lambda **_: LocalModel("actual-model-id", "http://127.0.0.1:9931/v1"))
    status = asyncio.run(health(modelMode="local-deepseek", taskTier="quick"))
    assert status["ready"] is True
    assert status["profile"] == "local-quick-direct"
    assert status["toolExecutionEnabled"] is False
    with pytest.raises(HTTPException) as exc:
        asyncio.run(query(QueryRequest(question="sample question", modelMode="deepseek", taskTier="quick")))
    assert exc.value.status_code == 422
