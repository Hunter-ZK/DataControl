import json

from dataagent_gateway.runner import parse_event_stream


def _stream(lines: list[dict]) -> str:
    return "\n".join(json.dumps(item, ensure_ascii=False) for item in lines)


def test_plan_metric_clarification_is_exposed_without_hidden_reasoning_or_sql():
    stream = _stream(
        [
            {"type": "session", "sessionId": "p2-session"},
            {"type": "thinking", "text": "private semantic reasoning"},
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
                        "phrase": "贷款增长",
                        "metric": None,
                        "researchPolicy": "internal_only",
                        "clarification": {
                            "id": "metric_choice",
                            "question": "“贷款增长”存在多个可用统计口径，请选择本次要使用的指标。",
                            "selection_mode": "single",
                            "allow_custom_input": True,
                            "options": [
                                {
                                    "id": "metric_loan_balance_yoy",
                                    "label": "贷款余额同比增长率",
                                    "description": "余额同比口径",
                                    "value": "metric_loan_balance_yoy",
                                },
                                {
                                    "id": "metric_new_loan_amount",
                                    "label": "新增贷款金额",
                                    "description": "期间发生额口径",
                                    "value": "metric_new_loan_amount",
                                },
                            ],
                        },
                    },
                    ensure_ascii=False,
                ),
            },
            {"type": "final", "text": "请选择一个可信统计口径后，我会继续原问题。"},
        ]
    )

    result = parse_event_stream(stream)
    assert result["sessionId"] == "p2-session"
    assert result["researchPolicy"] == "internal_only"
    assert result["clarification"]["selection_mode"] == "single"
    assert {item["value"] for item in result["clarification"]["options"]} == {
        "metric_loan_balance_yoy",
        "metric_new_loan_amount",
    }
    assert result["sql"] is None
    assert result["validationState"] == "not_applicable"
    assert result["hiddenReasoningExposed"] is False
    assert "private semantic reasoning" not in result["answer"]
    assert [event["tool"] for event in result["events"] if event["type"] == "tool_call"] == ["plan_metric"]
