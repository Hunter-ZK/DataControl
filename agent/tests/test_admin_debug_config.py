from dataagent_gateway.runner import _debug_capture_enabled, _redact_config_text


def test_debug_config_redacts_inline_secrets_but_keeps_env_variable_names():
    source = "apiKey: sk-very-secret-key-value\napiKeyEnv: DEEPSEEK_API_KEY\n"
    result = _redact_config_text(source)
    assert "sk-very-secret-key-value" not in result
    assert "apiKey: [REDACTED]" in result
    assert "apiKeyEnv: DEEPSEEK_API_KEY" in result


def test_debug_capture_can_be_disabled_explicitly(monkeypatch):
    monkeypatch.setenv("DATACONTROL_AGENT_DEBUG_CAPTURE", "0")
    assert _debug_capture_enabled() is False
    monkeypatch.setenv("DATACONTROL_AGENT_DEBUG_CAPTURE", "1")
    assert _debug_capture_enabled() is True
