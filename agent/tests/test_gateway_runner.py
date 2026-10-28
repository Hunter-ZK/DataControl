import asyncio
import json
import logging
from pathlib import Path
from types import SimpleNamespace

import pytest
import dataagent_gateway.runner as runner_module

from dataagent_gateway.runner import HarnessRunError, HeadlessHarnessRunner, parse_event_stream


def _stream(lines: list[dict]) -> str:
    return "\n".join(json.dumps(item, ensure_ascii=False) for item in lines)


def test_headless_event_stream_exposes_tools_but_not_hidden_reasoning():
    lines = [
        {"type": "session", "sessionId": "session-1", "cwd": "/repo"},
        {"type": "thinking", "text": "private reasoning must not leave gateway"},
        {
            "type": "tool_call",
            "callId": "m1",
            "tool": "mcp__agent3__resolve_metric",
            "input": {"phrase": "本期贷款余额"},
        },
        {
            "type": "tool_result",
            "callId": "m1",
            "status": "completed",
            "result": json.dumps(
                {
                    "resolved": True,
                    "metric": {
                        "id": "metric_loan_balance",
                        "name": "各项贷款余额",
                        "source_entity": "stat_prod.dws_loan_region_month",
                        "measure": "loan_balance",
                        "time_field": "stat_month",
                        "valid_dimensions": ["region_code"],
                        "caveats": "期末贷款余额",
                    },
                },
                ensure_ascii=False,
            ),
        },
        {
            "type": "tool_call",
            "callId": "c1",
            "tool": "mcp__agent3__compile_query",
            "input": {
                "metric_id": "metric_loan_balance",
                "dimensions": ["region_code"],
                "time_values": ["LATEST"],
            },
        },
        {
            "type": "tool_result",
            "callId": "c1",
            "status": "completed",
            "result": json.dumps(
                {
                    "sql": "SELECT region_code, SUM(loan_balance) FROM stat_prod.dws_loan_region_month GROUP BY region_code"
                }
            ),
        },
        {
            "type": "tool_call",
            "callId": "c2",
            "tool": "mcp__agent3__validate_sql",
            "input": {
                "sql": "SELECT region_code, SUM(loan_balance) FROM stat_prod.dws_loan_region_month GROUP BY region_code"
            },
        },
        {
            "type": "tool_result",
            "callId": "c2",
            "status": "completed",
            "result": json.dumps({"valid": True, "issues": []}),
        },
        {"type": "status", "phase": "turn_end", "turn": 1, "reason": "completed"},
        {
            "type": "final",
            "text": "## 结论\n**已生成**并校验本期贷款余额 SQL。\n\n- 来源表已确认\n- 口径已确认\n\n```sql\nSELECT 1;\n```",
        },
    ]
    result = parse_event_stream(_stream(lines))

    assert result["sessionId"] == "session-1"
    assert result["answer"].startswith("## 结论")
    assert "**已生成**" in result["answer"]
    assert "- 来源表已确认" in result["answer"]
    assert "```sql" not in result["answer"]
    assert "SELECT 1" not in result["answer"]
    assert result["summary"] == "结论"
    assert result["sql"].startswith("SELECT region_code")
    assert result["validation"]["valid"] is True
    assert result["validationState"] == "passed"
    assert result["sqlSourceCallId"] == "c2"
    assert result["validationCallId"] == "c2"
    assert result["sqlExecuted"] is False
    assert result["hiddenReasoningExposed"] is False
    assert all(item["type"] != "thinking" for item in result["events"])
    assert "private reasoning" not in result["answer"]
    assert result["evidence"]["metrics"][0]["code"] == "metric_loan_balance"
    assert result["evidence"]["period"]["resolved"] == "LATEST"
    assert result["evidence"]["dimensions"] == ["region_code"]
    assert result["evidence"]["caliber"] == "期末贷款余额"


def test_textual_compile_result_still_captures_generated_sql_without_claiming_validation():
    stream = _stream(
        [
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
                "result": "compiled SQL:\n```sql\nSELECT region_code, SUM(balance_amt) FROM dw.dwd_loan_snapshot GROUP BY region_code;\n```",
            },
            {"type": "final", "text": "done"},
        ]
    )
    result = parse_event_stream(stream)
    assert result["sql"].startswith("SELECT region_code")
    assert result["sql"].endswith(";")
    assert result["validation"] is None
    assert result["validationState"] == "not_validated"
    assert result["sqlSourceCallId"] == "c1"
    assert result["validationCallId"] is None


def test_latest_validation_is_bound_to_the_sql_submitted_to_that_validate_call():
    first_sql = "SELECT SUM(balance_amt) FROM dw.dwd_loan_snapshot"
    corrected_sql = (
        "SELECT SUM(balance_amt) FROM dw.dwd_loan_snapshot "
        "WHERE dt = '2026-08-31'"
    )
    stream = _stream(
        [
            {
                "type": "tool_call",
                "callId": "compile-1",
                "tool": "mcp__agent3__compile_query",
                "input": {"metric_id": "loan_balance"},
            },
            {
                "type": "tool_result",
                "callId": "compile-1",
                "status": "completed",
                "result": json.dumps({"sql": first_sql}),
            },
            {
                "type": "tool_call",
                "callId": "validate-1",
                "tool": "mcp__agent3__validate_sql",
                "input": {"sql": first_sql},
            },
            {
                "type": "tool_result",
                "callId": "validate-1",
                "status": "completed",
                "result": json.dumps(
                    {
                        "valid": False,
                        "issues": [{"code": "NON_ADDITIVE_OVER_TIME"}],
                    }
                ),
            },
            {
                "type": "tool_call",
                "callId": "compile-2",
                "tool": "mcp__agent3__compile_query",
                "input": {"metric_id": "loan_balance"},
            },
            {
                "type": "tool_result",
                "callId": "compile-2",
                "status": "completed",
                "result": json.dumps({"sql": corrected_sql}),
            },
            {
                "type": "tool_call",
                "callId": "validate-2",
                "tool": "mcp__agent3__validate_sql",
                "input": {"sql": corrected_sql},
            },
            {
                "type": "tool_result",
                "callId": "validate-2",
                "status": "completed",
                "result": json.dumps({"valid": True, "issues": []}),
            },
            {"type": "final", "text": "done"},
        ]
    )

    result = parse_event_stream(stream)
    assert result["sql"] == corrected_sql
    assert result["validation"]["valid"] is True
    assert result["validationState"] == "passed"
    assert result["sqlSourceCallId"] == "validate-2"
    assert result["validationCallId"] == "validate-2"


def test_later_unvalidated_compile_does_not_inherit_previous_validation():
    first_sql = "SELECT 1"
    second_sql = "SELECT 2"
    stream = _stream(
        [
            {
                "type": "tool_call",
                "callId": "compile-1",
                "tool": "mcp__agent3__compile_query",
                "input": {},
            },
            {
                "type": "tool_result",
                "callId": "compile-1",
                "status": "completed",
                "result": json.dumps({"sql": first_sql}),
            },
            {
                "type": "tool_call",
                "callId": "validate-1",
                "tool": "mcp__agent3__validate_sql",
                "input": {"sql": first_sql},
            },
            {
                "type": "tool_result",
                "callId": "validate-1",
                "status": "completed",
                "result": json.dumps({"valid": True, "issues": []}),
            },
            {
                "type": "tool_call",
                "callId": "compile-2",
                "tool": "mcp__agent3__compile_query",
                "input": {},
            },
            {
                "type": "tool_result",
                "callId": "compile-2",
                "status": "completed",
                "result": json.dumps({"sql": second_sql}),
            },
            {"type": "final", "text": "done"},
        ]
    )

    result = parse_event_stream(stream)
    assert result["sql"] == first_sql
    assert result["validation"]["valid"] is True
    assert result["validationState"] == "passed"
    assert result["validationCallId"] == "validate-1"


def test_non_agent3_tool_activity_is_not_exposed():
    stream = _stream(
        [
            {"type": "tool_call", "callId": "x", "tool": "shell", "input": {}},
            {
                "type": "tool_result",
                "callId": "x",
                "status": "completed",
                "result": "ok",
            },
            {"type": "final", "text": "done"},
        ]
    )
    result = parse_event_stream(stream)
    assert result["events"] == []


def test_headless_command_never_contains_user_question_and_rejects_shell_like_session_ids():
    runner = HeadlessHarnessRunner()
    command = runner._command("session-1234")
    assert command[-2:] == ["--session-id", "session-1234"]

    with pytest.raises(HarnessRunError, match="Invalid DataAgent session id"):
        runner._command("session-1 & whoami")


def test_windows_headless_command_uses_node_entrypoint_without_shell(monkeypatch):
    runner = HeadlessHarnessRunner()
    monkeypatch.setattr(runner_module, "os", SimpleNamespace(name="nt"))
    command = runner._command("session-1234")
    assert command[:1] == ["node"]
    assert Path(command[1]).as_posix().endswith("/@deepseek-ai/dsh/lib/bin.js")
    assert "cmd.exe" not in command
    assert command[-2:] == ["--session-id", "session-1234"]

def test_live_console_trace_logs_tools_without_payloads(caplog):
    reader = asyncio.StreamReader()
    secret = "private-token-and-hidden-reasoning"
    events = [
        {"type": "thinking", "text": secret},
        {"type": "tool_call", "tool": "mcp__agent3__validate_sql", "callId": "t1",
         "input": {"sql": f"SELECT '{secret}'"}},
        {"type": "tool_result", "callId": "t1", "status": "completed",
         "result": f"SELECT '{secret}'"},
        {"type": "tool_call", "tool": "untrusted-user-controlled-name", "callId": "t2",
         "input": {"api_key": secret}},
        {"type": "final", "text": secret},
    ]
    reader.feed_data(_stream(events).encode("utf-8"))
    reader.feed_eof()
    with caplog.at_level(logging.INFO, logger="uvicorn.error"):
        output = asyncio.run(HeadlessHarnessRunner()._capture_trace(reader, "test1234"))
    assert secret in output
    assert "TOOL_START validate_sql" in caplog.text
    assert "TOOL_END validate_sql status=completed" in caplog.text
    assert "TOOL_START harness_tool" in caplog.text
    assert secret not in caplog.text
    assert "SELECT" not in caplog.text


def test_console_trace_does_not_log_hidden_reasoning_or_raw_agent_content(caplog):
    reader = asyncio.StreamReader()
    reader.feed_data(_stream([
        {"type": "thinking", "text": "secret-thought"},
        {"type": "final", "text": "customer-secret"},
        {"type": "status", "phase": "turn_end", "reason": "completed"},
    ]).encode("utf-8"))
    reader.feed_eof()
    with caplog.at_level(logging.INFO, logger="uvicorn.error"):
        asyncio.run(HeadlessHarnessRunner()._capture_trace(reader, "test5678"))
    assert "secret-thought" not in caplog.text
    assert "customer-secret" not in caplog.text
