from langgraph.checkpoint.memory import InMemorySaver

from app.disclosure_agent import build_disclosure_agent


# 保存不同 thread_id 对应的会话状态。
MEMORY = InMemorySaver()

# 将记忆组件装入披露式 Agent。
MEMORY_AGENT = build_disclosure_agent(checkpointer=MEMORY)


def run_memory_agent(message: str, thread_id: str) -> dict:
    """在指定会话中运行带短期记忆的 Agent。"""
    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }

    return MEMORY_AGENT.invoke(
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