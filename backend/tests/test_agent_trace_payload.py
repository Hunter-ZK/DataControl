from backend.app.agent.history import _sanitize_trace_value


def test_debug_trace_redacts_credentials_but_keeps_sql_and_tool_payload():
    payload = {
        "tool": "validate_sql",
        "input": {"sql": "SELECT amount FROM dw.loan", "api_key": "not-for-display"},
        "output": {"status": "passed", "authorization": "Bearer secret-token"},
    }
    clean = _sanitize_trace_value(payload)
    assert clean["input"]["sql"] == "SELECT amount FROM dw.loan"
    assert clean["input"]["api_key"] == "[REDACTED]"
    assert clean["output"]["authorization"] == "[REDACTED]"


def test_debug_trace_redacts_bearer_tokens_inside_strings():
    clean = _sanitize_trace_value({"message": "Authorization: Bearer abcdefghijklmnop"})
    assert clean["message"] == "Authorization: Bearer [REDACTED]"



def test_public_answer_never_returns_full_trace_payloads():
    from backend.app.agent import history

    result = {
        "answer": "SQL 已生成",
        "events": [
            {"type": "tool_call", "tool": "validate_sql", "callId": "abc",
             "input": {"sql": "SELECT 1"}},
            {"type": "tool_result", "tool": "validate_sql", "callId": "abc",
             "status": "completed", "output": {"valid": True}},
        ],
        "sqlExecuted": False,
        "hiddenReasoningExposed": False,
    }
    safe = history._safe_answer(result)
    assert "input" not in safe["events"][0]
    assert "output" not in safe["events"][1]



def test_debug_trace_redacts_inline_secret_assignments():
    clean = _sanitize_trace_value({"message": "api_key=sk-12345678901234567890 password: hunter2"})
    assert "sk-12345678901234567890" not in clean["message"]
    assert "hunter2" not in clean["message"]
