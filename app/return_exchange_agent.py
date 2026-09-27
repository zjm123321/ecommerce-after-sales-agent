import json

from langchain_core.messages import AIMessage, SystemMessage
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from app.agent import MODEL
from app.tools import (
    create_return_exchange_review_ticket_tool,
    get_order_tool,
    search_return_exchange_policy_tool,
)


ORDER_PROMPT = """
你是电商售后退换货 Agent，当前负责验证订单。

规则：

1. 用户必须提供订单号。
2. 收到退换货请求后，必须先调用 get_order_tool 验证订单。
3. 不得相信用户声称的订单状态。
4. 订单不存在时，不得创建退换货审核工单。
5. 缺少订单号时，要求用户提供订单号。
6. 不得调用物流催办、退款审核或其他不属于退换货业务的工具。
"""


POLICY_PROMPT = """
你是电商售后退换货 Agent，当前负责查询退换货政策。

订单已经通过工具验证存在。

必须调用 search_return_exchange_policy_tool，并传入：

1. 已验证的订单号。
2. 用户原始退换货问题作为 query。

不得根据常识自行编写退换货政策。
"""


RETURN_EXCHANGE_PROMPT = """
你是电商售后退换货 Agent，当前负责提交退换货审核。

订单已经通过工具验证存在，退换货政策也已经通过工具查询。

现在调用 create_return_exchange_review_ticket_tool，
创建或复用内部退换货审核工单。

该工具只提交内部审核申请，不代表退货、换货或审核已经完成。
"""


FINAL_PROMPT = """
你是电商售后退换货 Agent，现在生成最终回复。

规则：

1. 只能根据当前消息中的 ToolMessage 回答。
2. created=true 只表示内部退换货审核工单已经创建或存在。
3. 不得声称退货、换货或审核已经完成。
4. 应说明工单仍需工作人员审核。
5. 如果政策工具返回了政策，必须说明政策标题和 source。
6. 只能解释政策工具返回的 content，不得补充或编造其他退换货条件。
7. 不得承诺审核结果、处理时效、上门取件或换货完成时间。
8. 政策 content 未明确提及时，不得建议用户准备照片、视频、凭证或其他材料。
9. 使用简洁中文回复。
"""


ORDER_MODEL = MODEL.bind_tools([get_order_tool])

POLICY_MODEL = MODEL.bind_tools(
    [search_return_exchange_policy_tool]
)

RETURN_EXCHANGE_MODEL = MODEL.bind_tools(
    [create_return_exchange_review_ticket_tool]
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


def call_return_exchange_agent(
    state: MessagesState,
) -> dict:
    messages = [
        SystemMessage(content=RETURN_EXCHANGE_PROMPT),
        *state["messages"],
    ]

    return {
        "messages": [
            RETURN_EXCHANGE_MODEL.invoke(messages)
        ]
    }


def generate_final_response(
    state: MessagesState,
) -> dict:
    """根据已验证的工具结果生成最终回复。"""
    messages = [
        SystemMessage(content=FINAL_PROMPT),
        *state["messages"],
    ]

    return {
        "messages": [
            MODEL.invoke(messages)
        ]
    }


def generate_rejection_response(
    state: MessagesState,
) -> dict:
    """根据工具结果生成确定性的拒绝回复。"""
    result = parse_last_tool_result(state)

    reason = (
        result.get("reason")
        or result.get("message")
        or "当前条件不符合退换货审核要求"
    )

    return {
        "messages": [
            AIMessage(
                content=(
                    f"{reason}，"
                    "未创建内部退换货审核工单。"
                )
            )
        ]
    }


def route_after_order(
    state: MessagesState,
) -> str:
    result = parse_last_tool_result(state)

    if result.get("found"):
        return "policy_agent"

    return "reject"


def route_after_policy(
    state: MessagesState,
) -> str:
    result = parse_last_tool_result(state)

    if result.get("found"):
        return "return_exchange_agent"

    return "reject"


def build_return_exchange_agent():
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
        ToolNode([search_return_exchange_policy_tool]),
    )

    graph.add_node(
        "return_exchange_agent",
        call_return_exchange_agent,
    )
    graph.add_node(
        "return_exchange_tools",
        ToolNode(
            [create_return_exchange_review_ticket_tool]
        ),
    )

    graph.add_node(
        "respond",
        generate_final_response,
    )
    graph.add_node(
        "reject",
        generate_rejection_response,
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
            "reject": "reject",
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
            "return_exchange_agent": "return_exchange_agent",
            "reject": "reject",
        },
    )

    graph.add_conditional_edges(
        "return_exchange_agent",
        tools_condition,
        {
            "tools": "return_exchange_tools",
            END: END,
        },
    )

    graph.add_edge(
        "return_exchange_tools",
        "respond",
    )
    graph.add_edge(
        "respond",
        END,
    )
    graph.add_edge(
        "reject",
        END,
    )

    return graph.compile()


RETURN_EXCHANGE_AGENT = build_return_exchange_agent()


def run_return_exchange_agent(
    message: str,
) -> dict:
    """运行带政策检索的退换货审核 Agent。"""
    return RETURN_EXCHANGE_AGENT.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": message,
                }
            ]
        }
    )
