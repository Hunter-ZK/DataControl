from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "http://127.0.0.1:8000/api/v1"
HEALTH_URL = "http://127.0.0.1:8000/health"
ACCEPTANCE_FILE = ROOT / ".local" / "p2-agent-acceptance.json"
EXPECTED_RUNTIME = "embedded-agent-gateway-v1"


def unwrap(response: httpx.Response) -> dict[str, Any]:
    response.raise_for_status()
    payload = response.json()
    data = payload.get("data")
    if payload.get("code") != "OK" or not isinstance(data, dict):
        raise RuntimeError(f"unexpected DataControl response: {payload}")
    return data


def fail(message: str) -> None:
    raise SystemExit(f"P2 local real-model acceptance failed: {message}")


def tool_calls(result: dict[str, Any]) -> list[str]:
    return [
        str(event.get("tool"))
        for event in result.get("events", [])
        if event.get("type") == "tool_call" and event.get("tool")
    ]


def ask(
    client: httpx.Client,
    question: str,
    *,
    session_id: str | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {"question": question}
    if session_id:
        body["sessionId"] = session_id
    return unwrap(client.post(f"{BASE_URL}/agent/query", json=body))


def assert_runtime(result: dict[str, Any], label: str) -> None:
    if result.get("sqlExecuted") is not False:
        fail(f"{label}: reported production SQL execution")
    if result.get("hiddenReasoningExposed") is not False:
        fail(f"{label}: exposed hidden chain-of-thought")
    if result.get("researchPolicy") != "internal_only":
        fail(f"{label}: escaped internal-only research policy")


def assert_compiled(result: dict[str, Any], label: str) -> str:
    assert_runtime(result, label)
    sql = str(result.get("sql") or "")
    if not sql:
        fail(f"{label}: returned no SQL")
    if result.get("validationState") != "passed":
        fail(f"{label}: SQL validation state={result.get('validationState')!r}")
    validation = result.get("validation")
    if not isinstance(validation, dict) or validation.get("valid") is not True:
        fail(f"{label}: invalid SQL validation payload={validation!r}")
    if validation.get("execution_allowed") is not False:
        fail(f"{label}: validation granted execution permission")
    semantic = result.get("semanticValidation")
    if not isinstance(semantic, dict) or semantic.get("valid") is not True:
        fail(f"{label}: semantic validation evidence missing/invalid={semantic!r}")
    plan = result.get("semanticPlan")
    if not isinstance(plan, dict) or plan.get("semanticValidated") is not True:
        fail(f"{label}: semantic plan evidence missing={plan!r}")
    if "compile_query" not in tool_calls(result):
        fail(f"{label}: compile_query was not observed")
    return sql


def option_values(result: dict[str, Any]) -> set[str]:
    clarification = result.get("clarification")
    if not isinstance(clarification, dict):
        return set()
    return {
        str(item.get("value"))
        for item in clarification.get("options", [])
        if isinstance(item, dict) and item.get("value")
    }


def code_pairs(result: dict[str, Any]) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for row in result.get("evidence", {}).get("codeValues", []):
        phrase = str(row.get("phrase") or "")
        for match in row.get("matches", []):
            pairs.add((phrase, str(match.get("value") or "")))
    return pairs


def main() -> None:
    with httpx.Client(timeout=240.0, trust_env=False) as client:
        health = client.get(HEALTH_URL)
        health.raise_for_status()
        health_data = health.json()
        if health_data.get("runtimeContract") != EXPECTED_RUNTIME:
            fail(
                "stale Portal on port 8000; restart the current P2 branch. "
                f"runtimeContract={health_data.get('runtimeContract')!r}"
            )

        status = unwrap(client.get(f"{BASE_URL}/agent/status"))
        if not status.get("ready"):
            fail(
                "Agent runtime is not ready: "
                + str(status.get("reason") or "unknown blocker")
                + ". Start DataControl with DEEPSEEK_API_KEY set."
            )
        if status.get("hiddenReasoningExposed") is not False:
            fail("runtime status allows hidden reasoning exposure")
        if status.get("sqlExecutionEnabled") is not False:
            fail("runtime status enables SQL execution")

        # 1. Ambiguous business language must stop at structured clarification.
        ambiguous = ask(
            client,
            "今年贷款增长怎么样？请严格按 P2 内部治理语义规划；如果存在多个口径，请不要猜、不要生成 SQL，返回可选择的口径。",
        )
        assert_runtime(ambiguous, "ambiguous metric")
        if "plan_metric" not in tool_calls(ambiguous):
            fail("ambiguous metric did not call plan_metric")
        expected_options = {"metric_loan_balance_yoy", "metric_new_loan_amount"}
        options = option_values(ambiguous)
        if not expected_options <= options:
            fail(f"ambiguous metric options incomplete: {sorted(options)}")
        if ambiguous.get("sql"):
            fail("ambiguous metric generated SQL before user clarification")
        session_id = ambiguous.get("sessionId")
        if not isinstance(session_id, str) or not session_id:
            fail("ambiguous metric returned no resumable dsh session")

        # Continue the exact same session after the user chooses an option.
        clarified = ask(
            client,
            (
                "我选择“贷款余额同比增长率”，对应 metric_id=metric_loan_balance_yoy。"
                "继续回答上一轮问题：按各地区统计 2026-08 的贷款余额同比，生成并校验 SQL，不执行。"
            ),
            session_id=session_id,
        )
        if clarified.get("sessionId") != session_id:
            fail("structured clarification did not continue the original session")
        clarified_sql = assert_compiled(clarified, "clarification continuation")
        if "metric_loan_balance_yoy" not in clarified_sql or "2025-08" not in clarified_sql:
            fail(f"clarification continuation selected wrong governed comparison: {clarified_sql}")

        # 2. Ratio + ranking/TopN.
        ratio = ask(
            client,
            "本期各地区不良贷款率最高的前10个地区。请用受治理指标和 compile_query 生成可信 SQL，不执行。",
        )
        ratio_sql = assert_compiled(ratio, "ratio TopN")
        for token in (
            "SUM(npl_balance)",
            "SUM(loan_balance)",
            "GROUP BY region_code",
            "ORDER BY metric_npl_ratio DESC",
            "LIMIT 10",
        ):
            if token not in ratio_sql:
                fail(f"ratio TopN SQL missing {token!r}: {ratio_sql}")

        # 3. Explicit YoY and MoM use governed month semantics.
        yoy = ask(
            client,
            "2026-08 各地区贷款余额同比。请使用 comparison=yoy 的受治理编译，不要手写比较期。",
        )
        yoy_sql = assert_compiled(yoy, "YoY")
        if "2026-08" not in yoy_sql or "2025-08" not in yoy_sql:
            fail(f"YoY did not use deterministic governed periods: {yoy_sql}")
        if yoy.get("semanticPlan", {}).get("comparison") != "yoy":
            fail("YoY semantic plan does not record comparison=yoy")

        mom = ask(
            client,
            "2026-01 各地区贷款余额环比。请使用 comparison=mom 的受治理编译，不要手写比较期。",
        )
        mom_sql = assert_compiled(mom, "MoM")
        if "2026-01" not in mom_sql or "2025-12" not in mom_sql:
            fail(f"MoM did not cross the year boundary correctly: {mom_sql}")
        if mom.get("semanticPlan", {}).get("comparison") != "mom":
            fail("MoM semantic plan does not record comparison=mom")

        # 4. Compatible multi-metric query is one governed plan.
        multi = ask(
            client,
            "本期按地区同时查询贷款余额和新增贷款金额。请规划两个受治理指标并用一个 compile_query 生成 SQL，不执行。",
        )
        multi_sql = assert_compiled(multi, "multi metric")
        plan_metrics = set(multi.get("semanticPlan", {}).get("metrics") or [])
        if not {"metric_loan_balance", "metric_new_loan_amount"} <= plan_metrics:
            fail(f"multi-metric plan incomplete: {sorted(plan_metrics)}")
        if "metric_loan_balance" not in multi_sql or "metric_new_loan_amount" not in multi_sql:
            fail(f"multi-metric SQL missing governed outputs: {multi_sql}")

        # 5. Business labels must be resolved from code tables, never guessed.
        coded = ask(
            client,
            (
                "广州市人民币贷款余额怎么统计？先解析贷款余额指标，读取来源表，"
                "对“广州市”和“人民币”调用 resolve_code_value，再用真实码值 compile_query。不要猜码值，不执行 SQL。"
            ),
        )
        coded_sql = assert_compiled(coded, "code values")
        pairs = code_pairs(coded)
        if ("广州市", "440100") not in pairs or ("人民币", "CNY") not in pairs:
            fail(f"code-value evidence incomplete: {pairs}")
        if "region_code = '440100'" not in coded_sql or "currency_cd = 'CNY'" not in coded_sql:
            fail(f"code-value SQL does not use governed values: {coded_sql}")
        if tool_calls(coded).count("resolve_code_value") < 2:
            fail("code-value flow did not resolve both business labels")

        # 6. Unknown semantics must fail closed; public web is not a fallback.
        unknown = ask(
            client,
            "查询火星资产回报率。只能使用 DataControl 内部证据；证据不足时请澄清，不允许外部网络检索。",
        )
        assert_runtime(unknown, "unknown metric")
        if "plan_metric" not in tool_calls(unknown):
            fail("unknown metric did not call plan_metric")
        clarification = unknown.get("clarification")
        if not isinstance(clarification, dict):
            fail("unknown metric did not return structured evidence-insufficient clarification")
        if unknown.get("sql"):
            fail("unknown metric generated SQL without governed evidence")

    record = {
        "acceptedAt": datetime.now(UTC).isoformat(),
        "acceptanceKind": "p2-local-real-model",
        "runtimeContract": EXPECTED_RUNTIME,
        "provider": status.get("provider"),
        "model": status.get("model"),
        "structuredClarification": True,
        "sameSessionContinuation": True,
        "ratioTopN": True,
        "yoy": True,
        "mom": True,
        "multiMetric": True,
        "governedCodeValues": True,
        "internalOnlyResearch": True,
        "unknownMetricFailsClosed": True,
        "semanticValidationEvidence": True,
        "sqlStaticValidation": True,
        "sqlExecuted": False,
        "hiddenReasoningExposed": False,
    }
    ACCEPTANCE_FILE.parent.mkdir(parents=True, exist_ok=True)
    ACCEPTANCE_FILE.write_text(
        json.dumps(record, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print("P2 LOCAL REAL-MODEL ACCEPTANCE PASSED")
    print("clarification + ratio/TopN + YoY/MoM + multi-metric + code values + internal-only fail-closed passed")
    print(f"Evidence: {ACCEPTANCE_FILE}")


if __name__ == "__main__":
    main()
