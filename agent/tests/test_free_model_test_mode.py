"""The optional free-test profile stays separate from official DeepSeek."""
from dataagent_gateway.runner import HeadlessHarnessRunner

def test_official_model_remains_default(monkeypatch):
    monkeypatch.delenv("DATACONTROL_AGENT_MODEL_MODE", raising=False)
    assert HeadlessHarnessRunner().profile == "dataagent-headless"

def test_public_gateway_can_be_selected_for_synthetic_testing(monkeypatch):
    monkeypatch.delenv("DATACONTROL_AGENT_MODEL_MODE", raising=False)
    free = HeadlessHarnessRunner(model_mode="free-test")
    assert free.profile == "dataagent-headless-free"
    assert free._command(None)[-3:] == ["--profile", "dataagent-headless-free", "--json"]
    monkeypatch.setenv("DATACONTROL_AGENT_MODEL_MODE", "free-test")
    assert HeadlessHarnessRunner().profile == "dataagent-headless-free"
