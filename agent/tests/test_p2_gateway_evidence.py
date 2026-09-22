import json

from dataagent_gateway.runner import parse_event_stream


def _stream(lines: list[dict]) -> str:
    return "\n".join(json.dumps(item, ensure_ascii=False) for item in lines)


def test_p2_gateway_keeps_governed_code_and_semantic_plan_evidence():
    sql = (
        "SELECT region_code, SUM(balance_amt) AS loan_balance "
        "FROM dw.dwd_loan_snapshot "
        "WHERE currency_cd = 'CNY' AND stat_month = '2026-08' "
        "GROUP BY region_code"
    )
    stream = _stream(
        [
            {"type": "session", "sessionId": "p2-session"},
            {
                "type": "tool_call",
                "callId": "code-1",
                "tool": "mcp__agent3__resolve_code_value",
                "input": {
                    "table_name": "dw.dwd_loan_snapshot",
                    "field": "currency_cd",
                    "phrase": "人民币",
                },
            },
            {
                "type": "tool_result",
                "callId": "code-1",
                "status": "completed",
                "result": json.dumps(
                    {
                        "status": "resolved",
                        "table": "dw.dwd_loan_snapshot",
                        "field": "currency_cd",
                        "codeTableNo": "CD_CURRENCY",
                        "matches": [
                            {
                                "code_table_no": "CD_CURRENCY",
                                "value": "CNY",
                                "name": "人民币",
                                "description": "人民币币种",
                            }
                        ],
                        "researchPolicy": "internal_only",
                    },
                    ensure_ascii=False,
                ),
            },
            {
                "type": "tool_call",
                "callId": "compile-1",
                "tool": "mcp__agent3__compile_query",
                "input": {
                    "metric_id": "loan_balance",
                    "dimensions": ["region_code"],
                    "time_values": ["2026-08"],
                    "filters": [{"field": "currency_cd", "op": "eq", "value": "CNY"}],
                },
            },
            {
                "type": "tool_result",
                "callId": "compile-1",
                "status": "completed",
                "result": json.dumps(
                    {
                        "sql": sql,
                        "validation": {
                            "valid": True,
                            "issues": [],
                            "operation": "query",
                            "risk_level": "low",
                            "execution_allowed": False,
                        },
                        "semanticValidation": {
                            "valid": True,
                            "issues": [],
                            "metricIds": ["loan_balance"],
                            "sourceEntity": "dw.dwd_loan_snapshot",
                            "timeField": "stat_month",
                            "researchPolicy": "internal_only",
                        },
                        "semanticPlan": {
                            "metrics": ["loan_balance"],
                            "dimensions": ["region_code"],
                            "filters": [
                                {"field": "currency_cd", "op": "eq", "value": "CNY"}
                            ],
                            "timeValues": ["2026-08"],
                            "comparison": "none",
                            "researchPolicy": "internal_only",
                            "semanticValidated": True,
                        },
                    },
                    ensure_ascii=False,
                ),
            },
            {"type": "final", "text": "已按内部口径生成查询。"},
        ]
    )

    result = parse_event_stream(stream)
    assert result["validationState"] == "passed"
    assert result["researchPolicy"] == "internal_only"
    assert result["semanticPlan"]["semanticValidated"] is True
    assert result["semanticValidation"]["valid"] is True
    assert result["evidence"]["dimensions"] == ["region_code"]
    resolved = result["evidence"]["codeValues"][0]
    assert resolved["phrase"] == "人民币"
    assert resolved["field"] == "currency_cd"
    assert resolved["matches"][0]["value"] == "CNY"
    assert any(event.get("tool") == "resolve_code_value" for event in result["events"])
    assert result["sqlExecuted"] is False
    assert result["hiddenReasoningExposed"] is False


def test_p2_gateway_drops_hidden_thinking_even_with_semantic_planning():
    result = parse_event_stream(
        _stream(
            [
                {"type": "thinking", "text": "secret chain of thought"},
                {
                    "type": "tool_call",
                    "callId": "plan-1",
                    "tool": "mcp__agent3__plan_metric",
                    "input": {"phrase": "贷款增长"},
                },
                {
                    "type": "tool_result",
                    "callId": "plan-1",
                    "status": "completed",
                    "result": json.dumps(
                        {
                            "status": "clarification_required",
                            "metric": None,
                            "clarification": {
                                "id": "metric_choice",
                                "question": "请选择贷款增长口径",
                                "selection_mode": "single",
                                "options": [
                                    {
                                        "id": "loan_balance_yoy",
                                        "label": "贷款余额同比增长率",
                                        "description": "同比口径",
                                        "value": "loan_balance_yoy",
                                    }
                                ],
                                "allow_custom_input": True,
                            },
                            "researchPolicy": "internal_only",
                        },
                        ensure_ascii=False,
                    ),
                },
                {"type": "final", "text": "存在多个内部可信口径，请选择。"},
            ]
        )
    )
    assert result["clarification"]["id"] == "metric_choice"
    assert result["researchPolicy"] == "internal_only"
    assert "secret chain of thought" not in result["answer"]
    assert all(event["type"] != "thinking" for event in result["events"])
