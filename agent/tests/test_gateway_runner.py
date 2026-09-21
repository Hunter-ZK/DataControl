import json

from dataagent_gateway.runner import parse_event_stream


def test_headless_event_stream_exposes_tools_but_not_hidden_reasoning():
    lines = [
        {"type": "session", "sessionId": "session-1", "cwd": "/repo"},
        {"type": "thinking", "text": "private reasoning must not leave gateway"},
        {"type": "tool_call", "callId": "m1", "tool": "mcp__agent3__resolve_metric", "input": {"phrase": "本期贷款余额"}},
        {"type": "tool_result", "callId": "m1", "status": "completed", "result": json.dumps({"resolved": True, "metric": {"id": "metric_loan_balance", "name": "各项贷款余额", "source_entity": "stat_prod.dws_loan_region_month", "measure": "loan_balance", "time_field": "stat_month", "valid_dimensions": ["region_code"], "caveats": "期末贷款余额"}}, ensure_ascii=False)},
        {"type": "tool_call", "callId": "c1", "tool": "mcp__agent3__compile_query", "input": {"metric_id": "metric_loan_balance", "dimensions": ["region_code"], "time_values": ["LATEST"]}},
        {"type": "tool_result", "callId": "c1", "status": "completed", "result": json.dumps({"sql": "SELECT region_code, SUM(loan_balance) FROM stat_prod.dws_loan_region_month GROUP BY region_code"})},
        {"type": "tool_call", "callId": "c2", "tool": "mcp__agent3__validate_sql", "input": {"sql": "SELECT region_code, SUM(loan_balance) FROM stat_prod.dws_loan_region_month GROUP BY region_code"}},
        {"type": "tool_result", "callId": "c2", "status": "completed", "result": json.dumps({"valid": True, "issues": []})},
        {"type": "status", "phase": "turn_end", "turn": 1, "reason": "completed"},
        {"type": "final", "text": "## 结论\n**已生成**并校验本期贷款余额 SQL。\n```sql\nSELECT 1;\n```"},
    ]
    result = parse_event_stream("\n".join(json.dumps(item, ensure_ascii=False) for item in lines))

    assert result["sessionId"] == "session-1"
    assert "**" not in result["answer"] and "```" not in result["answer"] and "##" not in result["answer"]
    assert result["sql"].startswith("SELECT region_code")
    assert result["validation"]["valid"] is True
    assert result["sqlExecuted"] is False
    assert result["hiddenReasoningExposed"] is False
    assert all(item["type"] != "thinking" for item in result["events"])
    assert result["evidence"]["metrics"][0]["code"] == "metric_loan_balance"
    assert result["evidence"]["period"]["resolved"] == "LATEST"
    assert result["evidence"]["dimensions"] == ["region_code"]
    assert result["evidence"]["caliber"] == "期末贷款余额"


def test_textual_mcp_result_still_captures_generated_sql():
    stream = "\n".join([
        json.dumps({"type": "tool_call", "callId": "c1", "tool": "mcp__agent3__compile_query", "input": {"metric_id": "loan_balance"}}),
        json.dumps({"type": "tool_result", "callId": "c1", "status": "completed", "result": "compiled SQL:\n```sql\nSELECT region_code, SUM(balance_amt) FROM dw.dwd_loan_snapshot GROUP BY region_code;\n```"}),
        json.dumps({"type": "final", "text": "done"}),
    ])
    result = parse_event_stream(stream)
    assert result["sql"].startswith("SELECT region_code")
    assert result["sql"].endswith(";")


def test_non_agent3_tool_activity_is_not_exposed():
    stream = "\n".join([
        json.dumps({"type": "tool_call", "callId": "x", "tool": "shell", "input": {}}),
        json.dumps({"type": "tool_result", "callId": "x", "status": "completed", "result": "ok"}),
        json.dumps({"type": "final", "text": "done"}),
    ])
    result = parse_event_stream(stream)
    assert result["events"] == []
