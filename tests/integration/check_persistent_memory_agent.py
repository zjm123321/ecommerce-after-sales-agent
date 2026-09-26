from uuid import uuid4

from langgraph.checkpoint.postgres import PostgresSaver

from app.database import CHECKPOINT_DATABASE_URL
from app.persistent_memory_agent import (
    run_persistent_memory_agent,
)


def collect_tool_calls(messages) -> list[dict]:
    """收集消息中的工具调用。"""
    calls = []

    for message in messages:
        for tool_call in getattr(message, "tool_calls", []) or []:
            calls.append(tool_call)

    return calls


def delete_test_thread(thread_id: str) -> None:
    """删除集成测试产生的 Checkpoint 数据。"""
    with PostgresSaver.from_conn_string(
        CHECKPOINT_DATABASE_URL
    ) as checkpointer:
        checkpointer.delete_thread(thread_id)


def test_postgres_restores_conversation_between_connections():
    """关闭并重新建立数据库连接后仍能恢复会话。"""
    thread_id = f"postgres-memory-test-{uuid4().hex}"

    try:
        first_result = run_persistent_memory_agent(
            "请帮我处理订单 ORD-1001，物流一直没到",
            thread_id,
        )
        first_message_count = len(first_result["messages"])

        # 函数内部的第一次数据库连接已经关闭。
        second_result = run_persistent_memory_agent(
            "刚才那个工单现在处理得怎么样了？",
            thread_id,
        )

        new_messages = second_result["messages"][
            first_message_count:
        ]
        tool_calls = collect_tool_calls(new_messages)

        assert [call["name"] for call in tool_calls] == [
            "get_ticket_status_tool"
        ]
        assert tool_calls[0]["args"]["ticket_id"].startswith(
            "TICKET-"
        )
        assert "pending" in second_result["messages"][-1].content
    finally:
        delete_test_thread(thread_id)