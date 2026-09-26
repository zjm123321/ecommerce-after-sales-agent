from langgraph.checkpoint.postgres import PostgresSaver

from app.database import CHECKPOINT_DATABASE_URL
from app.disclosure_agent import build_disclosure_agent


def run_persistent_memory_agent(
    message: str,
    thread_id: str,
) -> dict:
    """使用 PostgreSQL 保存和恢复指定会话的状态。"""
    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }

    with PostgresSaver.from_conn_string(
        CHECKPOINT_DATABASE_URL
    ) as checkpointer:
        agent = build_disclosure_agent(
            checkpointer=checkpointer
        )

        return agent.invoke(
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