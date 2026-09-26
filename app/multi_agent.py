from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, START, MessagesState, StateGraph

from app.classifier import IssueType
from app.disclosure_agent import DISCLOSURE_AGENT
from app.triage import AgentRoute, triage_message


class MultiAgentState(MessagesState):
    """多智能体之间共享的结构化状态。"""

    issue_type: IssueType
    route: AgentRoute


def get_latest_user_message(state: MultiAgentState) -> str:
    """取得当前会话中最近一条用户消息。"""
    for message in reversed(state["messages"]):
        if isinstance(message, HumanMessage):
            return str(message.content)

    raise ValueError("没有找到用户消息")


def triage_agent(state: MultiAgentState) -> dict:
    """识别问题类型并选择专家 Agent。"""
    message = get_latest_user_message(state)
    decision = triage_message(message)

    return {
        "issue_type": decision.issue_type,
        "route": decision.route,
    }


def refund_agent_placeholder(state: MultiAgentState) -> dict:
    """退款 Agent 占位节点，后续替换为真实实现。"""
    return {
        "messages": [
            AIMessage(
                content="已识别为退款问题，退款 Agent 尚未接入。"
            )
        ]
    }


def return_exchange_agent_placeholder(
    state: MultiAgentState,
) -> dict:
    """退换货 Agent 占位节点，后续替换为真实实现。"""
    return {
        "messages": [
            AIMessage(
                content="已识别为退换货问题，退换货 Agent 尚未接入。"
            )
        ]
    }


def human_handoff(state: MultiAgentState) -> dict:
    """无法自动处理的问题转交人工。"""
    return {
        "messages": [
            AIMessage(
                content="暂时无法识别或自动处理该问题，请联系人工客服。"
            )
        ]
    }


def route_to_specialist(state: MultiAgentState) -> AgentRoute:
    """根据 Triage 结果选择专家节点。"""
    return state["route"]


def build_multi_agent(
    logistics_agent=DISCLOSURE_AGENT,
):
    graph = StateGraph(MultiAgentState)

    graph.add_node("triage_agent", triage_agent)
    graph.add_node("logistics", logistics_agent)
    graph.add_node("refund", refund_agent_placeholder)
    graph.add_node(
        "return_exchange",
        return_exchange_agent_placeholder,
    )
    graph.add_node("human_handoff", human_handoff)

    graph.add_edge(START, "triage_agent")

    graph.add_conditional_edges(
        "triage_agent",
        route_to_specialist,
        {
            "logistics": "logistics",
            "refund": "refund",
            "return_exchange": "return_exchange",
            "human_handoff": "human_handoff",
        },
    )

    graph.add_edge("logistics", END)
    graph.add_edge("refund", END)
    graph.add_edge("return_exchange", END)
    graph.add_edge("human_handoff", END)

    return graph.compile()


MULTI_AGENT = build_multi_agent()


def run_multi_agent(message: str) -> MultiAgentState:
    """运行多智能体售后系统。"""
    return MULTI_AGENT.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": message,
                }
            ]
        }
    )