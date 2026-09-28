import json

from app.observability import record_agent_run


def test_record_successful_agent_run(monkeypatch):
    logged_messages = []

    monkeypatch.setattr(
        "app.observability.LOGGER.info",
        logged_messages.append,
    )

    event = record_agent_run(
        request_id="req-test",
        thread_id="thread-test",
        duration_ms=123.456,
        status="success",
        route="refund",
        issue_type="refund_request",
        tool_names=[
            "get_order_tool",
            "search_refund_policy_tool",
        ],
    )

    assert event["status"] == "success"
    assert event["duration_ms"] == 123.46
    assert event["tool_call_count"] == 2

    assert len(logged_messages) == 1

    logged_event = json.loads(logged_messages[0])

    assert logged_event["request_id"] == "req-test"
    assert logged_event["route"] == "refund"
    assert logged_event["tool_names"] == [
        "get_order_tool",
        "search_refund_policy_tool",
    ]

    assert "message" not in logged_event
    assert "tool_args" not in logged_event
    assert "api_key" not in logged_event


def test_record_failed_agent_run(monkeypatch):
    logged_messages = []

    monkeypatch.setattr(
        "app.observability.LOGGER.info",
        logged_messages.append,
    )

    event = record_agent_run(
        request_id="req-error",
        thread_id="thread-error",
        duration_ms=10,
        status="error",
        error_type="RuntimeError",
    )

    assert event["status"] == "error"
    assert event["error_type"] == "RuntimeError"
    assert event["route"] is None
    assert event["tool_names"] == []
    assert event["tool_call_count"] == 0