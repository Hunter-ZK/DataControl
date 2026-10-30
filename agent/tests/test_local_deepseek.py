"""Local llama.cpp discovery and native dsh provider configuration."""
import pytest
import httpx

from dataagent_gateway.local_provider import (
    LocalModel, LocalModelError, discover_local_model,
    profile_name, render_local_overlay, validated_base_url,
)


def test_local_endpoint_rejects_remote_and_unexpected_paths():
    for url in ("https://127.0.0.1:9931/v1", "http://evil.example:9931/v1",
                "http://127.0.0.1:9931/admin", "http://127.0.0.1:9931/v1?x=1",
                "http://user:pass@127.0.0.1:9931/v1"):
        with pytest.raises(LocalModelError):
            validated_base_url(url)
    assert validated_base_url("http://127.0.0.1:9931/v1") == "http://127.0.0.1:9931/v1"


def test_model_id_is_discovered_not_guessed(monkeypatch):
    original_client = httpx.Client
    def fake_client(*, trust_env, timeout):
        assert trust_env is False
        transport = httpx.MockTransport(lambda req: httpx.Response(
            200, json={"data": [{"id": "exact-llamacpp-id", "object": "model"}]}
        ))
        return original_client(transport=transport, trust_env=False, timeout=timeout)
    monkeypatch.setattr("dataagent_gateway.local_provider.httpx.Client", fake_client)
    monkeypatch.delenv("DATACONTROL_LOCAL_MODEL_ID", raising=False)
    item = discover_local_model()
    assert item.id == "exact-llamacpp-id"
    assert len(item.identity) == 12


def test_profile_preserves_mcp_and_guard_and_changes_provider_only(monkeypatch):
    source = ( "- id: llm-deepseek\n  config:\n    apiKeyEnv: DEEPSEEK_API_KEY\n"
               "- id: agent-default-model\n  config:\n"
               "    provider: deepseek-official\n    model: deepseek-flash\n"
               "- id: mcp-agent3\n- id: agent3-guard\n" )
    monkeypatch.delenv("DATACONTROL_LOCAL_CONTEXT_WINDOW", raising=False)
    monkeypatch.delenv("DATACONTROL_LOCAL_MAX_TOKENS", raising=False)
    text = render_local_overlay(source, LocalModel("id with spaces", "http://127.0.0.1:9931/v1"))
    assert 'model: "id with spaces"' in text
    assert 'id: "id with spaces"' in text
    assert "provider: local-llama" in text
    assert "api: openai-completions" in text
    assert "supportsDeveloperRole: false" in text
    assert "maxTokensField: max_tokens" in text
    assert "mcp-agent3" in text and "agent3-guard" in text
    assert profile_name("multi") == "dataagent-headless-local-multi"
