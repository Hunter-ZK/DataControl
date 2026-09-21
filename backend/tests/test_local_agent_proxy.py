from __future__ import annotations

import asyncio

import httpx

import backend.app.agent.runtime as runtime_module
from backend.app.agent.runtime import EmbeddedAgentGateway


def test_gateway_health_disables_environment_proxies(monkeypatch):
    captured: dict[str, object] = {}

    class DummyAsyncClient:
        def __init__(self, *args, **kwargs):
            captured.update(kwargs)

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url):
            request = httpx.Request("GET", url)
            return httpx.Response(200, request=request, json={"ready": True})

    monkeypatch.setattr(runtime_module.httpx, "AsyncClient", DummyAsyncClient)
    reachable, payload = asyncio.run(EmbeddedAgentGateway()._gateway_health())
    assert reachable is True
    assert payload["ready"] is True
    assert captured["trust_env"] is False
