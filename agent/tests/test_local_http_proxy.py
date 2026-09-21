from __future__ import annotations

import asyncio

import httpx

import agent3.metadata.datacontrol_http as metadata_http
import agent3.semantic.datacontrol as semantic_http
import dataagent_gateway.runner as gateway_runner
from agent3.metadata.datacontrol_http import PortalMetadataProvider
from agent3.semantic.datacontrol import load_portal_semantics
from dataagent_gateway.runner import HeadlessHarnessRunner, _with_loopback_no_proxy


def test_portal_metadata_provider_disables_environment_proxies(monkeypatch):
    captured: dict[str, object] = {}

    class DummyClient:
        def __init__(self, *args, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(metadata_http.httpx, "Client", DummyClient)
    PortalMetadataProvider("http://127.0.0.1:8000/api/v1")
    assert captured["trust_env"] is False


def test_semantic_bootstrap_disables_environment_proxies(monkeypatch):
    captured: dict[str, object] = {}
    closed = {"value": False}

    class DummyResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"code": "OK", "data": []}

    class DummyClient:
        def __init__(self, *args, **kwargs):
            captured.update(kwargs)

        def get(self, url):
            assert url == "http://127.0.0.1:8000/api/v1/metrics"
            return DummyResponse()

        def close(self):
            closed["value"] = True

    monkeypatch.setattr(semantic_http.httpx, "Client", DummyClient)
    registry = load_portal_semantics(
        "http://127.0.0.1:8000/api/v1",
        metadata=object(),  # no metrics means the provider is not dereferenced
    )
    assert captured["trust_env"] is False
    assert closed["value"] is True
    assert registry is not None


def test_gateway_mcp_health_disables_environment_proxies(monkeypatch):
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
            return httpx.Response(200, request=request, text="ok")

    monkeypatch.setattr(gateway_runner.httpx, "AsyncClient", DummyAsyncClient)
    assert asyncio.run(HeadlessHarnessRunner()._mcp_reachable()) is True
    assert captured["trust_env"] is False


def test_dsh_child_env_preserves_external_proxy_and_bypasses_loopback():
    env = _with_loopback_no_proxy({
        "HTTPS_PROXY": "http://proxy.example:7890",
        "NO_PROXY": "internal.example",
    })
    values = env["NO_PROXY"].split(",")
    assert "127.0.0.1" in values
    assert "localhost" in values
    assert "::1" in values
    assert "internal.example" in values
    assert env["no_proxy"] == env["NO_PROXY"]
    assert env["HTTPS_PROXY"] == "http://proxy.example:7890"


def test_mock_transport_remains_supported_for_portal_provider():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"code": "OK", "data": []})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = PortalMetadataProvider("http://portal/api/v1", client=client)
    assert provider.all_tables(authz=object()) == ()
    client.close()
