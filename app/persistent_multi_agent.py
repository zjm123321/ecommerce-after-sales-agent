import json
from typing import Any

from langchain_core.messages import (
    BaseMessage,
    SystemMessage,
    ToolMessage,
)
from langgraph.checkpoint.postgres import PostgresSaver

from app.database import CHECKPOINT_DATABASE_URL
from app.long_term_memory import (
    search_user_memories,
    upsert_user_memory,
)
from app.multi_agent import (
    LONG_TERM_MEMORY_PREFIX,
    build_multi_agent,
)


TICKET_MEMORY_TOOLS = {
    "create_logistics_expedite_ticket_tool",
    "create_refund_review_ticket_tool",
    "create_return_exchange_review_ticket_tool",
    "get_ticket_status_tool",
}

MEMORY_REFERENCE_WORDS = (
    "之前",
    "以前",
    "上次",
    "刚才",
    "那个",
    "历史",
    "工单",
)


def should_retrieve_long_term_memory(
    message: str,
) -> bool:
    """仅在用户引用历史事实时检索长期记忆。"""
    return any(
        word in message
        for word in MEMORY_REFERENCE_WORDS
    )


def parse_tool_message(
    message: ToolMessage,
) -> dict[str, Any] | None:
    """解析可信工具返回的数据。"""
    content = message.content

    if isinstance(content, dict):
        return content

    if isinstance(content, str):
        try:
            result = json.loads(content)
        except json.JSONDecodeError:
            return None

        if isinstance(result, dict):
            return result

    return None


def build_memory_system_message(
    memories: list[dict],
) -> SystemMessage | None:
    """将检索结果转换为不可执行的可信事实上下文。"""
    if not memories:
        return None

    facts = "\n".join(
        f"- {memory['content']}"
        for memory in memories
    )

    return SystemMessage(
        content=(
            f"{LONG_TERM_MEMORY_PREFIX}\n"
            f"{facts}"
        )
    )


def remember_verified_tickets(
    *,
    messages: list[BaseMessage],
    user_id: str,
    thread_id: str,
) -> None:
    """只从可信工具结果中提取并保存工单事实。"""
    for message in messages:
        if not isinstance(message, ToolMessage):
            continue

        if message.name not in TICKET_MEMORY_TOOLS:
            continue

        result = parse_tool_message(message)

        if result is None:
            continue

        ticket_id = result.get("ticket_id")
        order_id = result.get("order_id")
        status = result.get("status")

        if not ticket_id or not order_id or not status:
            continue

        issue_type = result.get(
            "issue_type",
            "unknown",
        )
        action = result.get(
            "action",
            "unknown",
        )

        content = (
            f"订单 {order_id} 的内部售后工单 "
            f"{ticket_id}，问题类型为 {issue_type}，"
            f"处理动作为 {action}，当前状态为 {status}。"
        )

        upsert_user_memory(
            user_id=user_id,
            memory_type="ticket",
            source_id=str(ticket_id),
            source_thread_id=thread_id,
            content=content,
        )


def run_persistent_multi_agent(
    message: str,
    thread_id: str,
    user_id: str | None = None,
) -> dict[str, Any]:
    """运行支持会话记忆和跨会话长期记忆的多智能体系统。"""
    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }

    with PostgresSaver.from_conn_string(
        CHECKPOINT_DATABASE_URL
    ) as checkpointer:
        agent = build_multi_agent(
            checkpointer=checkpointer,
        )

        previous_state = agent.get_state(config)
        previous_messages = previous_state.values.get(
            "messages",
            [],
        )
        previous_message_count = len(previous_messages)

        input_messages: list[dict | BaseMessage] = []

        if (
            user_id is not None
            and should_retrieve_long_term_memory(message)
        ):
            memories = search_user_memories(
                user_id=user_id,
                query=message,
                memory_type="ticket",
                limit=3,
            )
            memory_message = build_memory_system_message(
                memories
            )

            existing_memory_contents = {
                str(item.content)
                for item in previous_messages
                if isinstance(item, SystemMessage)
                and str(item.content).startswith(
                    LONG_TERM_MEMORY_PREFIX
                )
            }

            if (
                memory_message is not None
                and str(memory_message.content)
                not in existing_memory_contents
            ):
                input_messages.append(memory_message)

        input_messages.append(
            {
                "role": "user",
                "content": message,
            }
        )

        result = agent.invoke(
            {
                "messages": input_messages,
            },
            config=config,
        )

        all_messages = result["messages"]
        turn_messages = all_messages[
            previous_message_count:
        ]

        if user_id is not None:
            remember_verified_tickets(
                messages=turn_messages,
                user_id=user_id,
                thread_id=thread_id,
            )

        return {
            **result,
            "turn_messages": turn_messages,
        }