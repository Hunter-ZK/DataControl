"""Retired public gateway is rejected even if legacy environment flags remain."""
import pytest

from dataagent_gateway.runner import HeadlessHarnessRunner


def test_official_model_remains_default(monkeypatch):
    monkeypatch.delenv("DATACONTROL_AGENT_MODEL_MODE", raising=False)
    assert HeadlessHarnessRunner().profile == "dataagent-headless"


def test_public_gateway_cannot_be_selected(monkeypatch):
    monkeypatch.setenv("DATACONTROL_AGENT_MODEL_MODE", "free-test")
    with pytest.raises(ValueError, match="public gateway retired"):
        HeadlessHarnessRunner()
    with pytest.raises(ValueError, match="public gateway retired"):
        HeadlessHarnessRunner(model_mode="free-test")
