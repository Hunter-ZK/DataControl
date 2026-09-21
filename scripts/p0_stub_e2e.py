from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import IO

import httpx

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / ".local" / "p0-stub-e2e"
STUB_LOG = LOCAL / "stub_requests.jsonl"
INJECTION_MARKER = LOCAL / "prompt-injection-marker"


class Service:
    def __init__(self, name: str, command: list[str], *, cwd: Path, env: dict[str, str]):
        self.name = name
        self.command = command
        self.cwd = cwd
        self.env = env
        self.stdout_handle: IO[str] | None = None
        self.stderr_handle: IO[str] | None = None
        self.process: subprocess.Popen[str] | None = None

    def start(self) -> None:
        self.stdout_handle = (LOCAL / f"{self.name}.out.log").open("w", encoding="utf-8")
        self.stderr_handle = (LOCAL / f"{self.name}.err.log").open("w", encoding="utf-8")
        self.process = subprocess.Popen(
            self.command,
            cwd=self.cwd,
            env=self.env,
            stdin=subprocess.DEVNULL,
            stdout=self.stdout_handle,
            stderr=self.stderr_handle,
            text=True,
        )

    def stop(self) -> None:
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        if self.stdout_handle is not None:
            self.stdout_handle.close()
        if self.stderr_handle is not None:
            self.stderr_handle.close()

    def assert_alive(self) -> None:
        if self.process is not None and self.process.poll() is not None:
            stderr_path = LOCAL / f"{self.name}.err.log"
            detail = stderr_path.read_text(encoding="utf-8", errors="replace")[-4000:]
            raise RuntimeError(f"{self.name} exited early with code {self.process.returncode}:\n{detail}")


def wait_http(service: Service, url: str, timeout: float = 30.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        service.assert_alive()
        try:
            with httpx.Client(timeout=1.0, trust_env=False) as client:
                response = client.get(url)
            if response.status_code < 500:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.2)
    raise RuntimeError(f"{service.name} did not become reachable at {url}")


def wait_tcp(service: Service, host: str, port: int, timeout: float = 30.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        service.assert_alive()
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return
        except OSError:
            time.sleep(0.2)
    raise RuntimeError(f"{service.name} did not bind {host}:{port}")


def unwrap(response: httpx.Response) -> dict:
    response.raise_for_status()
    payload = response.json()
    if payload.get("code") != "OK" or not isinstance(payload.get("data"), dict):
        raise AssertionError(f"unexpected Portal envelope: {payload}")
    return payload["data"]


def assert_stub_received_prompt(prompt: str) -> None:
    rows = [json.loads(line) for line in STUB_LOG.read_text(encoding="utf-8").splitlines() if line]
    questions = [str(row.get("question") or "") for row in rows]
    if not any(prompt in question for question in questions):
        raise AssertionError(
            "DeepSeek stub did not receive the exact untrusted prompt through the harness input boundary; "
            f"captured questions={questions!r}"
        )


def main() -> None:
    LOCAL.mkdir(parents=True, exist_ok=True)
    STUB_LOG.unlink(missing_ok=True)
    INJECTION_MARKER.unlink(missing_ok=True)

    env = os.environ.copy()
    env.update(
        {
            "NO_PROXY": "127.0.0.1,localhost,::1",
            "no_proxy": "127.0.0.1,localhost,::1",
            "DEEPSEEK_API_KEY": "datacontrol-ci-stub-key",
            "DEEPSEEK_BASE_URL": "http://127.0.0.1:8999",
            "DATACONTROL_STUB_LOG": str(STUB_LOG),
            "DSH_TELEMETRY_MODE": "DISABLED",
            "AGENT3_MCP_POC_MODE": "1",
            "DATACONTROL_PORTAL_URL": "http://127.0.0.1:8000/api/v1",
        }
    )
    env.setdefault("DSH_HOME", str(ROOT / ".local" / "dsh-home"))

    services = [
        Service(
            "stub-llm",
            [
                sys.executable,
                "-m",
                "uvicorn",
                "scripts.stub_llm:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8999",
            ],
            cwd=ROOT,
            env=env,
        ),
        Service(
            "portal",
            [
                sys.executable,
                "-m",
                "uvicorn",
                "backend.app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8000",
            ],
            cwd=ROOT,
            env=env,
        ),
        Service(
            "agent3-mcp",
            [sys.executable, "-m", "agent3.adapters.mcp.server"],
            cwd=ROOT / "agent",
            env=env,
        ),
        Service(
            "agent-gateway",
            [
                sys.executable,
                "-m",
                "uvicorn",
                "dataagent_gateway.app:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8910",
            ],
            cwd=ROOT,
            env=env,
        ),
    ]

    try:
        services[0].start()
        wait_http(services[0], "http://127.0.0.1:8999/openapi.json")

        services[1].start()
        wait_http(services[1], "http://127.0.0.1:8000/health")

        services[2].start()
        wait_tcp(services[2], "127.0.0.1", 8900)

        services[3].start()
        wait_http(services[3], "http://127.0.0.1:8910/health", timeout=45.0)

        with httpx.Client(timeout=120.0, trust_env=False) as client:
            status = unwrap(client.get("http://127.0.0.1:8000/api/v1/agent/status"))
            if status.get("ready") is not True:
                raise AssertionError(f"DataAgent gateway is not ready: {status}")

            # Shell metacharacters are intentional. They must arrive at the model as
            # plain prompt text and must never become part of the dsh command line.
            prompt = (
                "本期各地区贷款余额是多少？请生成并校验 SQL；不要执行。 "
                f"& printf injected > {INJECTION_MARKER}"
            )
            result = unwrap(
                client.post(
                    "http://127.0.0.1:8000/api/v1/agent/query",
                    json={"question": prompt},
                )
            )

        required_tools = {"resolve_metric", "compile_query", "validate_sql"}
        observed_tools = {
            event.get("tool")
            for event in result.get("events", [])
            if event.get("type") == "tool_call"
        }
        missing_tools = required_tools - observed_tools
        if missing_tools:
            raise AssertionError(f"stub chain missed Agent3 tools: {sorted(missing_tools)}")

        sql = str(result.get("sql") or "")
        if "stat_prod.dws_loan_region_month" not in sql:
            raise AssertionError(f"unexpected SQL source: {sql}")
        if "region_code" not in sql or "GROUP BY region_code" not in sql:
            raise AssertionError(f"stub did not preserve the regional dimension: {sql}")
        if "MAX(stat_month)" not in sql:
            raise AssertionError(f"LATEST semantic was not compiled deterministically: {sql}")

        validation = result.get("validation")
        if result.get("validationState") != "passed":
            raise AssertionError(f"validation state is not passed: {result.get('validationState')!r}")
        if not isinstance(validation, dict) or validation.get("valid") is not True:
            raise AssertionError(f"bound validation payload is not valid: {validation!r}")
        if validation.get("execution_allowed") is not False:
            raise AssertionError("static validator incorrectly granted execution permission")
        if result.get("sqlSourceCallId") != result.get("validationCallId"):
            raise AssertionError(
                "displayed SQL and validation do not share one validate_sql evidence call"
            )
        if result.get("sqlExecuted") is not False:
            raise AssertionError("gateway reported SQL execution")
        if result.get("hiddenReasoningExposed") is not False:
            raise AssertionError("gateway exposed hidden reasoning")

        assert_stub_received_prompt(prompt)
        if INJECTION_MARKER.exists():
            raise AssertionError("prompt metacharacters escaped the model-input boundary and executed")

        print("P0 STUB E2E PASSED")
        print("Portal -> Gateway -> dsh -> MCP -> Agent3 -> validate_sql evidence is bound")
    finally:
        for service in reversed(services):
            service.stop()


if __name__ == "__main__":
    main()
