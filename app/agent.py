from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from app.local_config import DEEPSEEK_API_KEY
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

# 将工具说明交给模型，使模型能够选择工具。
MODEL_WITH_TOOLS = MODEL.bind_tools(TOOLS)


SYSTEM_PROMPT = """
你是电商售后物流处理 Agent。

处理规则：
1. 用户必须提供订单号。
2. 先调用 get_order_tool，确认订单存在。
3. 再调用 get_logistics_tool，查询物流状态。
4. 只有物流状态为 delayed 时，才能调用 create_logistics_expedite_ticket_tool。
5. 该工具只创建内部售后工单，不代表已经联系物流公司。
6. 不得声称已联系承运方、已经完成实际催办或保证送达时间。
7. 使用简洁中文向用户说明处理结果。
"""


def call_model(state: MessagesState) -> dict:
    """让模型读取对话和工具结果，并决定下一步操作。"""
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        *state["messages"],
    ]
    response = MODEL_WITH_TOOLS.invoke(messages)
    return {"messages": [response]}


def build_agent():
    graph = StateGraph(MessagesState)

    graph.add_node("agent", call_model)
    graph.add_node("tools", ToolNode(TOOLS))

    graph.add_edge(START, "agent")

    # 模型返回工具调用时进入 tools，否则结束。
    graph.add_conditional_edges(
        "agent",
        tools_condition,
        {
            "tools": "tools",
            END: END,
        },
    )

    # 工具执行结果重新交给模型判断。
    graph.add_edge("tools", "agent")

    return graph.compile()


AGENT = build_agent()


def run_agent(message: str) -> dict:
    """运行一次售后 Agent 对话。"""
    return AGENT.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": message,
                }
            ]
        }
    )