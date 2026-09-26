from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from app.local_config import DEEPSEEK_API_KEY
from app.prompts import BASELINE_PROMPT, OPTIMIZED_PROMPT
from app.tools import (
    create_logistics_expedite_ticket_tool,
    get_logistics_tool,
    get_order_tool,
)


TOOLS = [
    get_order_tool,
    get_logistics_tool,
    create_logistics_expedite_ticket_tool,
]


MODEL = ChatOpenAI(
    model="deepseek-chat",
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com",
    temperature=0,
    timeout=20,
    max_retries=2,
)

MODEL_WITH_TOOLS = MODEL.bind_tools(TOOLS)


def build_agent(system_prompt: str):
    """使用指定提示词构建 Agent。"""

    def call_model(state: MessagesState) -> dict:
        messages = [
            SystemMessage(content=system_prompt),
            *state["messages"],
        ]
        response = MODEL_WITH_TOOLS.invoke(messages)
        return {"messages": [response]}

    graph = StateGraph(MessagesState)

    graph.add_node("agent", call_model)
    graph.add_node("tools", ToolNode(TOOLS))

    graph.add_edge(START, "agent")

    graph.add_conditional_edges(
        "agent",
        tools_condition,
        {
            "tools": "tools",
            END: END,
        },
    )

    graph.add_edge("tools", "agent")

    return graph.compile()


# 两个版本只使用不同提示词，其余模型和工具完全相同。
AGENTS = {
    "baseline": build_agent(BASELINE_PROMPT),
    "optimized": build_agent(OPTIMIZED_PROMPT),
}


def run_agent(
    message: str,
    prompt_version: str = "optimized",
) -> dict:
    """使用指定提示词版本运行售后 Agent。"""
    if prompt_version not in AGENTS:
        raise ValueError(
            f"未知提示词版本：{prompt_version}"
        )

    return AGENTS[prompt_version].invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": message,
                }
            ]
        }
    )