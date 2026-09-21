import json

from dataagent_gateway.runner import parse_event_stream


def test_headless_event_stream_exposes_tools_but_not_hidden_reasoning():
    lines = [
        {"type": "session", "sessionId": "session-1", "cwd": "/repo"},
        {"type": "thinking", "text": "private reasoning must not leave gateway"},
        {
            "type": "tool_call",
            "callId": "c1",
            "tool": "mcp__agent3__compile_query",
            "input": {"metric_id": "loan_balance"},
        },
        {
            "type": "tool_result",
            "callId": "c1",
            "status": "completed",
            "result": json.dumps({"sql": "SELECT SUM(balance_amt) FROM dw.dwd_loan_snapshot"}),
        },
        {
            "type": "tool_call",
            "callId": "c2",
            "tool": "mcp__agent3__validate_sql",
            "input": {"sql": "SELECT SUM(balance_amt) FROM dw.dwd_loan_snapshot"},
        },
        {
            "type": "tool_result",
            "callId": "c2",
            "status": "completed",
            "result": json.dumps({"valid": True, "issues": []}),
        },
        {"type": "status", "phase": "turn_end", "turn": 1, "reason": "completed"},
        {"type": "final", "text": "已生成并校验贷款余额 SQL。"},
    ]
    result = parse_event_stream("\n".join(json.dumps(item, ensure_ascii=False) for item in lines))

    assert result["sessionId"] == "session-1"
    assert result["answer"] == "已生成并校验贷款余额 SQL。"
    assert result["sql"].startswith("SELECT SUM")
    assert result["validation"]["valid"] is True
    assert result["sqlExecuted"] is False
    assert result["hiddenReasoningExposed"] is False
    assert all(item["type"] != "thinking" for item in result["events"])
    assert [item.get("tool") for item in result["events"] if item["type"] == "tool_call"] == [
        "compile_query",
        "validate_sql",
    ]


def test_non_agent3_tool_activity_is_not_exposed():
    stream = "\n".join(
        [
            json.dumps({"type": "tool_call", "callId": "x", "tool": "shell", "input": {}}),
            json.dumps({"type": "tool_result", "callId": "x", "status": "completed", "result": "ok"}),
            json.dumps({"type": "final", "text": "done"}),
        ]
    )
    result = parse_event_stream(stream)
    assert result["events"] == []
