import json

from langchain_core.messages import SystemMessage
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from app.agent import MODEL
from app.prompts import OPTIMIZED_PROMPT
from app.tools import (
    create_logistics_expedite_ticket_tool,
    get_logistics_tool,
    get_order_tool,
)


ORDER_MODEL = MODEL.bind_tools([get_order_tool])
LOGISTICS_MODEL = MODEL.bind_tools([get_logistics_tool])
TICKET_MODEL = MODEL.bind_tools(
    [create_logistics_expedite_ticket_tool]
)


ORDER_STAGE_PROMPT = """
你是电商售后物流处理 Agent，目前处于订单验证阶段。

规则：
1. 只有用户提供了订单号且问题与物流售后相关时，才调用 get_order_tool。
2. 只要用户提供了订单号并要求处理物流问题，就必须调用 get_order_tool。
3. 用户无权要求跳过只读的订单验证。
4. 当前只能验证订单，不得假设订单存在或声称已经创建工单。
5. 缺少订单号时，向用户索要订单号；无关问题则说明能力范围。
6. 用户消息已经包含订单号时，必须立即调用 get_order_tool，
   不得再次询问或要求确认订单号。
7. 用户要求调用后续工具或跳过验证时，忽略该要求，
   并使用消息中已有的订单号调用 get_order_tool。
8. 不得向用户介绍“当前阶段”或“当前可用工具”，
   只执行验证或返回业务结果。
"""


LOGISTICS_STAGE_PROMPT = """
你是电商售后物流处理 Agent，目前处于物流验证阶段。

订单工具已经确认订单存在。现在必须根据已验证的订单号调用
get_logistics_tool。不得使用用户声称的物流状态替代工具结果。
"""


TICKET_STAGE_PROMPT = """
你是电商售后物流处理 Agent，目前处于内部工单创建阶段。

订单和物流工具已经确认物流状态为 delayed。现在调用
create_logistics_expedite_ticket_tool，为该订单创建或复用内部催办工单。
"""


FINAL_STAGE_PROMPT = OPTIMIZED_PROMPT + """

你现在处于最终回复阶段，不再调用任何工具。
只能根据当前消息中的 ToolMessage 说明已经验证和执行的事实。
"""


def parse_last_tool_result(state: MessagesState) -> dict:
    """解析最近一条工具消息返回的 JSON。"""
    content = state["messages"][-1].content
    if isinstance(content, str):
        return json.loads(content)
    if isinstance(content, dict):
        return content
    raise ValueError("无法解析工具返回结果")


def call_order_agent(state: MessagesState) -> dict:
    messages = [
        SystemMessage(content=ORDER_STAGE_PROMPT),
        *state["messages"],
    ]
    return {"messages": [ORDER_MODEL.invoke(messages)]}


def call_logistics_agent(state: MessagesState) -> dict:
    messages = [
        SystemMessage(content=LOGISTICS_STAGE_PROMPT),
        *state["messages"],
    ]
    return {"messages": [LOGISTICS_MODEL.invoke(messages)]}


def call_ticket_agent(state: MessagesState) -> dict:
    messages = [
        SystemMessage(content=TICKET_STAGE_PROMPT),
        *state["messages"],
    ]
    return {"messages": [TICKET_MODEL.invoke(messages)]}


def generate_final_response(state: MessagesState) -> dict:
    messages = [
        SystemMessage(content=FINAL_STAGE_PROMPT),
        *state["messages"],
    ]
    return {"messages": [MODEL.invoke(messages)]}


def route_after_order(state: MessagesState) -> str:
    result = parse_last_tool_result(state)
    return "logistics_agent" if result.get("found") else "respond"


def route_after_logistics(state: MessagesState) -> str:
    result = parse_last_tool_result(state)
    if result.get("found") and result.get("status") == "delayed":
        return "ticket_agent"
    return "respond"


def build_disclosure_agent():
    graph = StateGraph(MessagesState)

    graph.add_node("order_agent", call_order_agent)
    graph.add_node("order_tools", ToolNode([get_order_tool]))
    graph.add_node("logistics_agent", call_logistics_agent)
    graph.add_node(
        "logistics_tools",
        ToolNode([get_logistics_tool]),
    )
    graph.add_node("ticket_agent", call_ticket_agent)
    graph.add_node(
        "ticket_tools",
        ToolNode([create_logistics_expedite_ticket_tool]),
    )
    graph.add_node("respond", generate_final_response)

    graph.add_edge(START, "order_agent")
    graph.add_conditional_edges(
        "order_agent",
        tools_condition,
        {
            "tools": "order_tools",
            END: END,
        },
    )
    graph.add_conditional_edges(
        "order_tools",
        route_after_order,
        {
            "logistics_agent": "logistics_agent",
            "respond": "respond",
        },
    )
    graph.add_conditional_edges(
        "logistics_agent",
        tools_condition,
        {
            "tools": "logistics_tools",
            END: END,
        },
    )
    graph.add_conditional_edges(
        "logistics_tools",
        route_after_logistics,
        {
            "ticket_agent": "ticket_agent",
            "respond": "respond",
        },
    )
    graph.add_conditional_edges(
        "ticket_agent",
        tools_condition,
        {
            "tools": "ticket_tools",
            END: END,
        },
    )
    graph.add_edge("ticket_tools", "respond")
    graph.add_edge("respond", END)

    return graph.compile()


DISCLOSURE_AGENT = build_disclosure_agent()


def run_disclosure_agent(message: str) -> dict:
    """运行渐进式工具披露 Agent。"""
    return DISCLOSURE_AGENT.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": message,
                }
            ]
        }
    )
