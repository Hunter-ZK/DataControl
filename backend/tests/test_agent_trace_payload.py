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
