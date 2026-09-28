import json

from langchain_core.messages import ToolMessage

from app.persistent_multi_agent import (
    build_memory_system_message,
    remember_verified_tickets,
    should_retrieve_long_term_memory,
)


def test_history_reference_triggers_memory_retrieval():
    assert should_retrieve_long_term_memory(
        "我之前那个工单怎么样了？"
    ) is True

    assert should_retrieve_long_term_memory(
        "请处理订单 ORD-1001"
    ) is False


def test_build_memory_system_message():
    message = build_memory_system_message(
        [
            {
                "content": (
                    "订单 ORD-1001 的工单 "
                    "TICKET-TEST-001 当前为 pending。"
                )
            }
        ]
    )

    assert message is not None
    assert "可信长期记忆" in str(message.content)
    assert "TICKET-TEST-001" in str(message.content)


def test_verified_ticket_tool_result_is_remembered(
    monkeypatch,
):
    captured = []

    monkeypatch.setattr(
        "app.persistent_multi_agent.upsert_user_memory",
        lambda **kwargs: captured.append(kwargs),
    )

    tool_message = ToolMessage(
        name="create_logistics_expedite_ticket_tool",
        tool_call_id="call-test-001",
        content=json.dumps(
            {
                "ticket_id": "TICKET-TEST-001",
                "order_id": "ORD-1001",
                "issue_type": "delivery_delay",
                "action": "expedite_logistics",
                "status": "pending",
            }
        ),
    )

    remember_verified_tickets(
        messages=[tool_message],
        user_id="user-test-001",
        thread_id="thread-test-001",
    )

    assert len(captured) == 1
    assert captured[0]["user_id"] == "user-test-001"
    assert captured[0]["source_id"] == "TICKET-TEST-001"
    assert captured[0]["memory_type"] == "ticket"


def test_untrusted_tool_result_is_not_remembered(
    monkeypatch,
):
    captured = []

    monkeypatch.setattr(
        "app.persistent_multi_agent.upsert_user_memory",
        lambda **kwargs: captured.append(kwargs),
    )

    tool_message = ToolMessage(
        name="unknown_tool",
        tool_call_id="call-test-002",
        content=json.dumps(
            {
                "ticket_id": "TICKET-FAKE",
                "order_id": "ORD-FAKE",
                "status": "pending",
            }
        ),
    )

    remember_verified_tickets(
        messages=[tool_message],
        user_id="user-test-001",
        thread_id="thread-test-001",
    )

    assert captured == []