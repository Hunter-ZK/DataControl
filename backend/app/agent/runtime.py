from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from backend.app.core.config import (
    AGENT_GATEWAY_URL,
    AGENT_HOME,
    AGENT_TIMEOUT_SECONDS,
    MODEL_NAME,
    MODEL_PROVIDER,
)


class AgentRuntimeError(RuntimeError):
    pass


@dataclass(frozen=True)
class RuntimeStatus:
    ready: bool
    mode: str
    source: str
    gatewayUrl: str
    provider: str
    model: str
    sourceMigrated: bool
    sessionBridgeImplemented: bool
    integrated: bool
    realModelAccepted: bool
    serviceReachable: bool
    nextGate: str | None = None
    reason: str | None = None


class EmbeddedAgentGateway:
    """Portal-side gateway to the DataAgent subsystem owned by this monorepo."""

    def __init__(self) -> None:
        self.agent_home = Path(AGENT_HOME)
        self.gateway_url = AGENT_GATEWAY_URL
        self.timeout = AGENT_TIMEOUT_SECONDS

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def _manifest(self) -> dict[str, Any]:
        return self._read_json(self.agent_home / "runtime-manifest.json")

    def _local_acceptance(self) -> dict[str, Any]:
        return self._read_json(self.agent_home.parent / ".local" / "p3-agent-acceptance.json")

    async def _gateway_health(self) -> tuple[bool, dict[str, Any]]:
        try:
            async with httpx.AsyncClient(timeout=1.5) as client:
                response = await client.get(f"{self.gateway_url}/health")
                payload = response.json() if response.content else {}
                return response.is_success, payload if isinstance(payload, dict) else {}
        except (httpx.HTTPError, ValueError):
            return False, {}

    async def status(self) -> RuntimeStatus:
        manifest = self._manifest()
        acceptance = self._local_acceptance()
        source_migrated = bool(manifest.get("sourceMigrated"))
        bridge_implemented = bool(manifest.get("sessionBridgeImplemented"))
        local_accepted = bool(
            acceptance.get("sessionResumed")
            and acceptance.get("mcpToolObserved")
            and acceptance.get("validateSqlObserved")
            and acceptance.get("sqlGenerated")
            and acceptance.get("sqlExecuted") is False
            and acceptance.get("hiddenReasoningExposed") is False
            and acceptance.get("destructiveRequestExecuted") is False
        )
        real_model_accepted = bool(manifest.get("realModelAccepted")) or local_accepted
        integrated = bool(manifest.get("integrated")) or real_model_accepted
        next_gate = None if real_model_accepted else (
            str(manifest.get("nextGate")) if manifest.get("nextGate") else None
        )
        reachable = False
        gateway_health: dict[str, Any] = {}
        reason: str | None = None

        if not self.agent_home.exists():
            reason = f"embedded agent directory is missing: {self.agent_home}"
        elif not source_migrated:
            reason = "embedded DataAgent source migration is incomplete"
        elif not bridge_implemented:
            reason = "embedded DataAgent headless session bridge is not implemented"
        else:
            reachable, gateway_health = await self._gateway_health()
            if not reachable:
                reason = f"embedded agent gateway is not reachable at {self.gateway_url}"
            elif not gateway_health.get("ready"):
                reason = str(gateway_health.get("reason") or "embedded Agent runtime is degraded")

        ready = bool(bridge_implemented and reachable and gateway_health.get("ready"))
        return RuntimeStatus(
            ready=ready,
            mode="embedded-monorepo",
            source="DataControl/agent",
            gatewayUrl=self.gateway_url,
            provider=MODEL_PROVIDER,
            model=MODEL_NAME,
            sourceMigrated=source_migrated,
            sessionBridgeImplemented=bridge_implemented,
            integrated=integrated,
            realModelAccepted=real_model_accepted,
            serviceReachable=reachable,
            nextGate=next_gate,
            reason=reason,
        )

    async def run(self, prompt: str, *, session_id: str | None = None) -> dict[str, Any]:
        status = await self.status()
        if not status.ready:
            raise AgentRuntimeError(status.reason or "embedded Agent runtime is not ready")
        body: dict[str, Any] = {"question": prompt}
        if session_id:
            body["sessionId"] = session_id
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(f"{self.gateway_url}/v1/query", json=body)
                response.raise_for_status()
                payload = response.json()
        except httpx.TimeoutException as exc:
            raise AgentRuntimeError(f"Agent request exceeded {self.timeout:g}s timeout") from exc
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:1200]
            raise AgentRuntimeError(
                f"embedded agent gateway returned HTTP {exc.response.status_code}: {detail}"
            ) from exc
        except httpx.HTTPError as exc:
            raise AgentRuntimeError(f"embedded agent gateway call failed: {exc}") from exc
        if not isinstance(payload, dict):
            raise AgentRuntimeError("embedded agent gateway returned an invalid response")
        if payload.get("sqlExecuted") is True:
            raise AgentRuntimeError("embedded agent violated DataControl policy: SQL execution is forbidden")
        if payload.get("hiddenReasoningExposed") is True:
            raise AgentRuntimeError("embedded agent violated DataControl policy: hidden reasoning exposure")
        payload.setdefault("sqlExecuted", False)
        payload.setdefault("hiddenReasoningExposed", False)
        return payload
