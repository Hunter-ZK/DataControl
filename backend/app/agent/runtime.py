from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from backend.app.core.config import AGENT_GATEWAY_URL, AGENT_HOME, AGENT_TIMEOUT_SECONDS, MODEL_NAME, MODEL_PROVIDER


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
    integrated: bool
    serviceReachable: bool
    nextGate: str | None = None
    reason: str | None = None


class EmbeddedAgentGateway:
    """Portal-side gateway to the DataAgent subsystem owned by this monorepo.

    The Portal never imports Agent3 Core directly and never owns the model loop.
    `DataAgent-dsh` is provenance only; runtime code must resolve under DataControl/agent.
    """

    def __init__(self) -> None:
        self.agent_home = Path(AGENT_HOME)
        self.gateway_url = AGENT_GATEWAY_URL
        self.timeout = AGENT_TIMEOUT_SECONDS

    def _manifest(self) -> dict[str, Any]:
        path = self.agent_home / "runtime-manifest.json"
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    async def status(self) -> RuntimeStatus:
        manifest = self._manifest()
        source_migrated = bool(manifest.get("sourceMigrated"))
        integrated = bool(manifest.get("integrated"))
        next_gate = str(manifest.get("nextGate")) if manifest.get("nextGate") else None
        reachable = False
        reason: str | None = None
        if not self.agent_home.exists():
            reason = f"embedded agent directory is missing: {self.agent_home}"
        elif not source_migrated:
            reason = "embedded DataAgent source migration is incomplete"
        elif not integrated:
            reason = f"embedded DataAgent source is migrated; integration gate pending: {next_gate or 'runtime E2E'}"
        else:
            try:
                async with httpx.AsyncClient(timeout=1.5) as client:
                    response = await client.get(f"{self.gateway_url}/health")
                    reachable = response.is_success
                    if not reachable:
                        reason = f"embedded agent gateway returned HTTP {response.status_code}"
            except httpx.HTTPError:
                reason = f"embedded agent gateway is not reachable at {self.gateway_url}"
        return RuntimeStatus(
            ready=integrated and reachable,
            mode="embedded-monorepo",
            source="DataControl/agent",
            gatewayUrl=self.gateway_url,
            provider=MODEL_PROVIDER,
            model=MODEL_NAME,
            sourceMigrated=source_migrated,
            integrated=integrated,
            serviceReachable=reachable,
            nextGate=next_gate,
            reason=reason,
        )

    async def run(self, prompt: str) -> dict[str, Any]:
        status = await self.status()
        if not status.ready:
            raise AgentRuntimeError(status.reason or "embedded Agent runtime is not ready")
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(f"{self.gateway_url}/v1/query", json={"question": prompt})
                response.raise_for_status()
                payload = response.json()
        except httpx.TimeoutException as exc:
            raise AgentRuntimeError(f"Agent request exceeded {self.timeout:g}s timeout") from exc
        except httpx.HTTPStatusError as exc:
            raise AgentRuntimeError(f"embedded agent gateway returned HTTP {exc.response.status_code}: {exc.response.text[:1000]}") from exc
        except httpx.HTTPError as exc:
            raise AgentRuntimeError(f"embedded agent gateway call failed: {exc}") from exc
        if not isinstance(payload, dict):
            raise AgentRuntimeError("embedded agent gateway returned an invalid response")
        if payload.get("sqlExecuted") is True:
            raise AgentRuntimeError("embedded agent violated DataControl policy: SQL execution is forbidden")
        payload.setdefault("sqlExecuted", False)
        return payload
