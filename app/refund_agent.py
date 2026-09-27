import json

from langchain_core.messages import SystemMessage
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from app.agent import MODEL
from app.tools import (
    create_refund_review_ticket_tool,
    get_order_tool,
    search_refund_policy_tool,
)


ORDER_PROMPT = """
你是电商售后退款 Agent，当前负责验证订单。

规则：

1. 用户必须提供订单号。
2. 收到退款请求后，必须先调用 get_order_tool 验证订单。
3. 不得相信用户声称的订单状态。
4. 订单不存在时，不得创建退款审核工单。
5. 缺少订单号时，要求用户提供订单号。
6. 不得调用物流催办或其他不属于退款业务的工具。
"""


POLICY_PROMPT = """
你是电商售后退款 Agent，当前负责查询退款政策。

订单已经通过工具验证存在。

必须调用 search_refund_policy_tool，并传入：

1. 已验证的订单号。
2. 用户原始退款问题作为 query。

不得根据常识自行编写退款政策。
"""


REFUND_PROMPT = """
你是电商售后退款 Agent，当前负责提交退款审核。

订单已经通过工具验证存在，退款政策也已经通过工具查询。

现在调用 create_refund_review_ticket_tool，
创建或复用内部退款审核工单。

该工具只提交内部审核申请，不直接执行退款。
"""


FINAL_PROMPT = """
你是电商售后退款 Agent，现在生成最终回复。

规则：

1. 只能根据当前消息中的 ToolMessage 回答。
2. created=true 只表示内部退款审核工单已经创建或存在。
3. 不得声称退款已经完成、审核已经通过或款项已经到账。
4. 应说明工单仍需工作人员审核。
5. 如果政策工具返回了政策，必须说明政策标题和 source。
6. 只能解释政策工具返回的 content，不得补充或编造其他退款条件。
7. 不得承诺审核结果、退款金额、到账时间或处理时效。
8. 使用简洁中文回复。
"""


ORDER_MODEL = MODEL.bind_tools([get_order_tool])

POLICY_MODEL = MODEL.bind_tools(
    [search_refund_policy_tool]
)

REFUND_MODEL = MODEL.bind_tools(
    [create_refund_review_ticket_tool]
)


def parse_last_tool_result(
    state: MessagesState,
) -> dict:
    """解析最近一条工具消息返回的 JSON。"""
    content = state["messages"][-1].content

    if isinstance(content, str):
        return json.loads(content)

    if isinstance(content, dict):
        return content

    raise ValueError("无法解析工具返回结果")


def call_order_agent(
    state: MessagesState,
) -> dict:
    messages = [
        SystemMessage(content=ORDER_PROMPT),
        *state["messages"],
    ]

    return {
        "messages": [
            ORDER_MODEL.invoke(messages)
        ]
    }


def call_policy_agent(
    state: MessagesState,
) -> dict:
    messages = [
        SystemMessage(content=POLICY_PROMPT),
        *state["messages"],
    ]

    return {
        "messages": [
            POLICY_MODEL.invoke(messages)
        ]
    }


def call_refund_agent(
    state: MessagesState,
) -> dict:
    messages = [
        SystemMessage(content=REFUND_PROMPT),
        *state["messages"],
    ]

    return {
        "messages": [
            REFUND_MODEL.invoke(messages)
        ]
    }


def generate_final_response(
    state: MessagesState,
) -> dict:
    messages = [
        SystemMessage(content=FINAL_PROMPT),
        *state["messages"],
    ]

    return {
        "messages": [
            MODEL.invoke(messages)
        ]
    }


def route_after_order(
    state: MessagesState,
) -> str:
    result = parse_last_tool_result(state)

    if result.get("found"):
        return "policy_agent"

    return "respond"


def route_after_policy(
    state: MessagesState,
) -> str:
    result = parse_last_tool_result(state)

    if result.get("found"):
        return "refund_agent"

    return "respond"


def build_refund_agent():
    graph = StateGraph(MessagesState)

    graph.add_node(
        "order_agent",
        call_order_agent,
    )
    graph.add_node(
        "order_tools",
        ToolNode([get_order_tool]),
    )

    graph.add_node(
        "policy_agent",
        call_policy_agent,
    )
    graph.add_node(
        "policy_tools",
        ToolNode([search_refund_policy_tool]),
    )

    graph.add_node(
        "refund_agent",
        call_refund_agent,
    )
    graph.add_node(
        "refund_tools",
        ToolNode(
            [create_refund_review_ticket_tool]
        ),
    )

    graph.add_node(
        "respond",
        generate_final_response,
    )

    graph.add_edge(
        START,
        "order_agent",
    )

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
            "policy_agent": "policy_agent",
            "respond": "respond",
        },
    )

    graph.add_conditional_edges(
        "policy_agent",
        tools_condition,
        {
            "tools": "policy_tools",
            END: END,
        },
    )

    graph.add_conditional_edges(
        "policy_tools",
        route_after_policy,
        {
            "refund_agent": "refund_agent",
            "respond": "respond",
        },
    )

    graph.add_conditional_edges(
        "refund_agent",
        tools_condition,
        {
            "tools": "refund_tools",
            END: END,
        },
    )

    graph.add_edge(
        "refund_tools",
        "respond",
    )
    graph.add_edge(
        "respond",
        END,
    )

    return graph.compile()


REFUND_AGENT = build_refund_agent()


def run_refund_agent(
    message: str,
) -> dict:
    """运行带政策检索的退款审核 Agent。"""
    return REFUND_AGENT.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": message,
                }
            ]
        }
    )