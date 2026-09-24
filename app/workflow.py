from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.classifier import classify_message
from app.data import get_order


class TicketState(TypedDict, total=False):
    order_id: str
    message: str
    issue_type: str
    order: dict
    action: str
    response: str
    error: str


#  关键词判断
#  def classify_issue(state: TicketState) -> dict:
#     """Classify only delivery-related questions in the first prototype."""
#     delivery_words = ("物流", "快递", "没到", "延迟", "晚了", "送到")
#     issue_type = "delivery_delay" if any(word in state["message"] for word in delivery_words) else "unknown"
#     return {"issue_type": issue_type}

def classify_issue(state: TicketState) -> dict:
    """使用 DeepSeek 识别售后问题类型。"""
    issue_type = classify_message(state["message"])
    return {"issue_type": issue_type}


def load_order(state: TicketState) -> dict:
    """Load the order from the in-memory mock data."""
    order = get_order(state["order_id"])
    if order is None:
        return {"error": "订单不存在"}
    return {"order": order}


def generate_resolution(state: TicketState) -> dict:
    """Return an expedite action only for a valid delivery question."""
    if state.get("error"):
        return {
            "action": "manual_service",
            "response": "没有找到该订单，请联系人工客服。",
        }
    if state["issue_type"] != "delivery_delay":
        return {
            "action": "manual_service",
            "response": "暂时无法识别该问题，请联系人工客服。",
        }
    product = state["order"]["product"]
    return {
        "action": "expedite_logistics",
        "response": f"已为订单中的{product}创建物流催办。",
    }


def build_workflow():
    graph = StateGraph(TicketState)
    graph.add_node("classify_issue", classify_issue)
    graph.add_node("load_order", load_order)
    graph.add_node("generate_resolution", generate_resolution)
    graph.add_edge(START, "classify_issue")
    graph.add_edge("classify_issue", "load_order")
    graph.add_edge("load_order", "generate_resolution")
    graph.add_edge("generate_resolution", END)
    return graph.compile()


WORKFLOW = build_workflow()


def handle_ticket(order_id: str, message: str) -> TicketState:
    return WORKFLOW.invoke({"order_id": order_id, "message": message})

