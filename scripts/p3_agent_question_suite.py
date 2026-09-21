from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
BANK = ROOT / ".local" / "p3-question-bank.json"
REPORT = ROOT / ".local" / "p3-question-suite-report.json"
BASE_URL = "http://127.0.0.1:8000/api/v1"


def unwrap(response: httpx.Response) -> Any:
    response.raise_for_status()
    return response.json()["data"]


def evaluate(case: dict[str, Any], result: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if not result.get("answer"):
        failures.append("missing answer")
    if result.get("sqlExecuted") is not False:
        failures.append("sqlExecuted must be false")
    if result.get("hiddenReasoningExposed") is not False:
        failures.append("hiddenReasoningExposed must be false")

    evidence = result.get("evidence") if isinstance(result.get("evidence"), dict) else {}
    metric_codes = {
        str(row.get("code"))
        for row in evidence.get("metrics", [])
        if isinstance(row, dict) and row.get("code")
    }
    expected_metric = case.get("expectedMetric")
    if expected_metric and expected_metric not in metric_codes:
        failures.append(f"expected metric {expected_metric}, got {sorted(metric_codes)}")

    if case.get("kind") == "query":
        sql = str(result.get("sql") or "")
        if not sql:
            failures.append("missing SQL")
        tools = {
            str(event.get("tool"))
            for event in result.get("events", [])
            if isinstance(event, dict) and event.get("type") == "tool_call"
        }
        for required in ("resolve_metric", "compile_query", "validate_sql"):
            if required not in tools:
                failures.append(f"missing tool call {required}")
        expected_time = case.get("expectedTime")
        period = evidence.get("period") if isinstance(evidence.get("period"), dict) else {}
        if expected_time and period.get("resolved") != expected_time:
            failures.append(f"expected time {expected_time}, got {period.get('resolved')}")
        for dimension in case.get("expectedDimensions", []):
            if dimension not in sql:
                failures.append(f"SQL missing dimension {dimension}")
        validation = result.get("validation")
        if isinstance(validation, dict):
            valid = validation.get("valid")
            if valid is False:
                failures.append("validation returned invalid")
    return failures


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the P3 real-model Agent question bank against a live DataControl instance.")
    parser.add_argument("--limit", type=int, default=12, help="Number of cases to run; ignored with --all")
    parser.add_argument("--all", action="store_true", help="Run all question-bank cases (may consume significant model quota)")
    args = parser.parse_args()

    if not BANK.exists():
        raise SystemExit("Question bank is missing. Run scripts/setup-dev.ps1 or samples/generate_p3_question_bank.py first.")
    payload = json.loads(BANK.read_text(encoding="utf-8"))
    cases = payload.get("cases", [])
    selected = cases if args.all else cases[: max(1, args.limit)]

    results: list[dict[str, Any]] = []
    with httpx.Client(timeout=180.0) as client:
        status = unwrap(client.get(f"{BASE_URL}/agent/status"))
        if not status.get("ready"):
            raise SystemExit(f"Agent is not ready: {status.get('reason')}")
        for index, case in enumerate(selected, 1):
            print(f"[{index}/{len(selected)}] {case['id']} {case['question']}")
            try:
                result = unwrap(client.post(f"{BASE_URL}/agent/query", json={"question": case["question"]}))
                failures = evaluate(case, result)
                results.append({"id": case["id"], "question": case["question"], "passed": not failures, "failures": failures})
                print("  PASS" if not failures else "  FAIL: " + "; ".join(failures))
            except Exception as exc:  # acceptance runner should retain per-case diagnostics
                results.append({"id": case["id"], "question": case["question"], "passed": False, "failures": [str(exc)]})
                print(f"  ERROR: {exc}")

    passed = sum(1 for row in results if row["passed"])
    report = {
        "runAt": datetime.now(UTC).isoformat(),
        "count": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "passRate": round(passed / len(results), 4) if results else 0,
        "results": results,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nP3 QUESTION SUITE: {passed}/{len(results)} passed ({report['passRate']:.1%})")
    print(f"Report: {REPORT}")
    if passed != len(results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
