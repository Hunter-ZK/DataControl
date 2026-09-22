from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import IO, Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / ".local" / "p2-stub-e2e"
STUB_LOG = LOCAL / "stub_requests.jsonl"


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
            path = LOCAL / f"{self.name}.err.log"
            detail = path.read_text(encoding="utf-8", errors="replace")[-5000:]
            raise RuntimeError(
                f"{self.name} exited early with code {self.process.returncode}:\n{detail}"
            )


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


def unwrap(response: httpx.Response) -> dict[str, Any]:
    response.raise_for_status()
    payload = response.json()
    if payload.get("code") != "OK" or not isinstance(payload.get("data"), dict):
        raise AssertionError(f"unexpected Portal envelope: {payload}")
    return payload["data"]


def ask(client: httpx.Client, question: str) -> dict[str, Any]:
    return unwrap(
        client.post(
            "http://127.0.0.1:8000/api/v1/agent/query",
            json={"question": question},
        )
    )


def tools(result: dict[str, Any]) -> list[str]:
    return [
        str(event.get("tool"))
        for event in result.get("events", [])
        if event.get("type") == "tool_call"
    ]


def assert_common(result: dict[str, Any], *, expect_sql: bool = True) -> None:
    if result.get("researchPolicy") != "internal_only":
        raise AssertionError(f"P2 escaped internal-only research policy: {result}")
    if result.get("sqlExecuted") is not False:
        raise AssertionError("P2 reported production SQL execution")
    if result.get("hiddenReasoningExposed") is not False:
        raise AssertionError("P2 exposed hidden chain-of-thought")
    if expect_sql:
        if result.get("validationState") != "passed":
            raise AssertionError(f"P2 SQL validation did not pass: {result.get('validation')}")
        validation = result.get("validation")
        if not isinstance(validation, dict) or validation.get("valid") is not True:
            raise AssertionError(f"P2 SQL validation payload is not valid: {validation!r}")
        if validation.get("execution_allowed") is not False:
            raise AssertionError("P2 validator granted execution permission")
        semantic = result.get("semanticValidation")
        if not isinstance(semantic, dict) or semantic.get("valid") is not True:
            raise AssertionError(f"P2 semantic plan is not valid: {semantic!r}")
        plan = result.get("semanticPlan")
        if not isinstance(plan, dict) or plan.get("semanticValidated") is not True:
            raise AssertionError(f"P2 semantic plan evidence is missing: {plan!r}")


def assert_ambiguous(result: dict[str, Any]) -> None:
    assert_common(result, expect_sql=False)
    clarification = result.get("clarification")
    if not isinstance(clarification, dict):
        raise AssertionError(f"ambiguous metric did not return structured clarification: {result}")
    if clarification.get("selection_mode") != "single":
        raise AssertionError(f"unexpected clarification mode: {clarification}")
    values = {
        str(item.get("value"))
        for item in clarification.get("options", [])
        if isinstance(item, dict)
    }
    expected = {"metric_loan_balance_yoy", "metric_new_loan_amount"}
    if not expected <= values:
        raise AssertionError(f"ambiguous metric options are incomplete: {sorted(values)}")
    if result.get("sql"):
        raise AssertionError("ambiguous metric produced SQL before user clarification")
    if "plan_metric" not in tools(result):
        raise AssertionError("ambiguous flow skipped governed metric planning")


def assert_ratio(result: dict[str, Any]) -> None:
    assert_common(result)
    sql = str(result.get("sql") or "")
    required = [
        "CASE WHEN SUM(loan_balance) = 0 THEN NULL",
        "SUM(npl_balance) / SUM(loan_balance)",
        "GROUP BY region_code",
        "ORDER BY metric_npl_ratio DESC LIMIT 10",
    ]
    if any(token not in sql for token in required):
        raise AssertionError(f"ratio TopN SQL is not governed as expected: {sql}")
    plan = result["semanticPlan"]
    if plan.get("metrics") != ["metric_npl_ratio"] or plan.get("limit") != 10:
        raise AssertionError(f"ratio semantic plan is incorrect: {plan}")
    if not {"plan_metric", "compile_query"} <= set(tools(result)):
        raise AssertionError(f"ratio flow missed semantic tools: {tools(result)}")


def assert_code_values(result: dict[str, Any]) -> None:
    assert_common(result)
    sql = str(result.get("sql") or "")
    if "region_code = '440100'" not in sql or "currency_cd = 'CNY'" not in sql:
        raise AssertionError(f"business labels were not compiled to governed codes: {sql}")
    code_values = result.get("evidence", {}).get("codeValues", [])
    pairs: set[tuple[str, str]] = set()
    for row in code_values:
        phrase = str(row.get("phrase") or "")
        for match in row.get("matches", []):
            pairs.add((phrase, str(match.get("value") or "")))
    if ("人民币", "CNY") not in pairs or ("广州市", "440100") not in pairs:
        raise AssertionError(f"governed code-value evidence is incomplete: {pairs}")
    if tools(result).count("resolve_code_value") != 2:
        raise AssertionError(f"code-value flow did not resolve both labels: {tools(result)}")


def assert_multi(result: dict[str, Any]) -> None:
    assert_common(result)
    sql = str(result.get("sql") or "")
    if "SUM(loan_balance) AS metric_loan_balance" not in sql:
        raise AssertionError(f"primary metric missing from multi-metric SQL: {sql}")
    if "SUM(new_loan_amount) AS metric_new_loan_amount" not in sql:
        raise AssertionError(f"secondary metric missing from multi-metric SQL: {sql}")
    plan = result["semanticPlan"]
    if set(plan.get("metrics") or []) != {"metric_loan_balance", "metric_new_loan_amount"}:
        raise AssertionError(f"multi-metric semantic plan is incorrect: {plan}")


def assert_yoy(result: dict[str, Any]) -> None:
    assert_common(result)
    sql = str(result.get("sql") or "")
    if "'2026-08'" not in sql or "'2025-08'" not in sql:
        raise AssertionError(f"YoY periods are not deterministic: {sql}")
    if "AS metric_loan_balance_yoy" not in sql:
        raise AssertionError(f"YoY output alias missing: {sql}")
    if result["semanticPlan"].get("comparison") != "yoy":
        raise AssertionError(f"YoY semantic plan missing comparison: {result['semanticPlan']}")


def main() -> None:
    LOCAL.mkdir(parents=True, exist_ok=True)
    STUB_LOG.unlink(missing_ok=True)

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
            [sys.executable, "-m", "uvicorn", "scripts.stub_llm:app", "--host", "127.0.0.1", "--port", "8999"],
            cwd=ROOT,
            env=env,
        ),
        Service(
            "portal",
            [sys.executable, "-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", "8000"],
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
            [sys.executable, "-m", "uvicorn", "dataagent_gateway.app:app", "--host", "127.0.0.1", "--port", "8910"],
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

            ambiguous = ask(client, "[P2_AMBIGUOUS] 今年贷款增长怎么样？")
            assert_ambiguous(ambiguous)

            ratio = ask(client, "[P2_RATIO] 本期各地区不良贷款率最高的前10个地区")
            assert_ratio(ratio)

            code = ask(client, "[P2_CODE] 广州市人民币贷款余额怎么统计？")
            assert_code_values(code)

            multi = ask(client, "[P2_MULTI] 本期各地区贷款余额和新增贷款金额")
            assert_multi(multi)

            yoy = ask(client, "[P2_YOY] 2026-08 各地区贷款余额同比")
            assert_yoy(yoy)

        rows = [
            json.loads(line)
            for line in STUB_LOG.read_text(encoding="utf-8").splitlines()
            if line
        ]
        questions = [str(row.get("question") or "") for row in rows]
        for marker in ["P2_AMBIGUOUS", "P2_RATIO", "P2_CODE", "P2_MULTI", "P2_YOY"]:
            if not any(marker in question for question in questions):
                raise AssertionError(f"stub did not receive P2 scenario {marker}")

        print("P2 STUB E2E PASSED")
        print("Structured clarification + ratio TopN + code values + multi-metric + YoY are governed end-to-end")
        print("Research policy remains internal_only; production SQL execution and hidden CoT remain disabled")
    finally:
        for service in reversed(services):
            service.stop()


if __name__ == "__main__":
    main()
