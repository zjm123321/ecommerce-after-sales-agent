from typing import Any

from langgraph.checkpoint.postgres import PostgresSaver

from app.database import CHECKPOINT_DATABASE_URL
from app.multi_agent import build_multi_agent


def run_persistent_multi_agent(
    message: str,
    thread_id: str,
) -> dict[str, Any]:
    """运行具有 PostgreSQL 持久化记忆的多智能体系统。"""
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

        result = agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": message,
                    }
                ]
            },
            config=config,
        )

        all_messages = result["messages"]

        return {
            **result,
            "turn_messages": all_messages[
                previous_message_count:
            ],
        }