from __future__ import annotations

import httpx

import agent3.metadata.datacontrol_http as metadata_http
import agent3.semantic.datacontrol as semantic_http
from agent3.metadata.datacontrol_http import PortalMetadataProvider
from agent3.semantic.datacontrol import load_portal_semantics


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


def test_mock_transport_remains_supported_for_portal_provider():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"code": "OK", "data": []})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = PortalMetadataProvider("http://portal/api/v1", client=client)
    assert provider.all_tables(authz=object()) == ()
    client.close()
