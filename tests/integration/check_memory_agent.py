from uuid import uuid4

from app.memory_agent import run_memory_agent


def collect_tool_calls(messages) -> list[dict]:
    """收集消息中的工具调用。"""
    calls = []

    for message in messages:
        for tool_call in getattr(message, "tool_calls", []) or []:
            calls.append(tool_call)

    return calls


def test_same_thread_can_query_previous_ticket():
    """同一 thread_id 能根据历史工单查询最新状态。"""
    thread_id = f"memory-test-{uuid4().hex}"

    first_result = run_memory_agent(
        "请帮我处理订单 ORD-1001，物流一直没到",
        thread_id,
    )
    first_message_count = len(first_result["messages"])

    second_result = run_memory_agent(
        "刚才那个工单现在处理得怎么样了？",
        thread_id,
    )
    new_messages = second_result["messages"][first_message_count:]
    tool_calls = collect_tool_calls(new_messages)

    assert [call["name"] for call in tool_calls] == [
        "get_ticket_status_tool"
    ]
    assert tool_calls[0]["args"]["ticket_id"].startswith("TICKET-")


def test_different_threads_do_not_share_memory():
    """不同 thread_id 之间不能共享订单和工单信息。"""
    first_thread = f"memory-test-a-{uuid4().hex}"
    second_thread = f"memory-test-b-{uuid4().hex}"

    first_result = run_memory_agent(
        "请帮我处理订单 ORD-1001，物流一直没到",
        first_thread,
    )
    first_response = first_result["messages"][-1].content

    second_result = run_memory_agent(
        "刚才那个工单现在处理得怎么样了？",
        second_thread,
    )
    second_tool_calls = collect_tool_calls(second_result["messages"])
    second_response = second_result["messages"][-1].content

    assert "TICKET-" in first_response
    assert second_tool_calls == []
    assert "TICKET-9FD8DF614368" not in second_response
    assert "工单号" in second_response