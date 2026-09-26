from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.classifier import classify_message
from app.data import get_order
from app.ticket_service import create_ticket


class TicketState(TypedDict, total=False):
    order_id: str
    message: str
    issue_type: str
    order: dict
    action: str
    response: str
    error_code: str
    error_message: str
    ticket_id: str


#  关键词判断
#  def classify_issue(state: TicketState) -> dict:
#     """Classify only delivery-related questions in the first prototype."""
#     delivery_words = ("物流", "快递", "没到", "延迟", "晚了", "送到")
#     issue_type = "delivery_delay" if any(word in state["message"] for word in delivery_words) else "unknown"
#     return {"issue_type": issue_type}

def classify_issue(state: TicketState) -> dict:
    """使用 DeepSeek 识别售后问题类型。"""
    try:
        issue_type = classify_message(state["message"])
        return {"issue_type": issue_type}
    except Exception as exc:
        return {
            "issue_type": "unknown",
            "error_code": "classification_failed",
            "error_message": str(exc),
        }


def load_order(state: TicketState) -> dict:
    """Load the order from the in-memory mock data."""
    if state.get("error_code"):
        return {}

    order = get_order(state["order_id"])
    if order is None:
        return {
            "error_code": "order_not_found",
            "error_message": "订单不存在",
        }

    return {"order": order}


def generate_resolution(state: TicketState) -> dict:
    """根据工作流状态生成售后处理结果。"""
    if state.get("error_code") == "classification_failed":
        return {
            "action": "manual_service",
            "response": "问题识别服务暂时不可用，请联系人工客服。",
        }

    if state.get("error_code") == "order_not_found":
        return {
            "action": "manual_service",
            "response": "没有找到该订单，请联系人工客服。",
        }

    if state["issue_type"] != "delivery_delay":
        return {
            "action": "manual_service",
            "response": "暂时无法处理该问题，请联系人工客服。",
        }

    product = state["order"]["product"]

    try:
        ticket = create_ticket(
            order_id=state["order_id"],
            issue_type=state["issue_type"],
            action="expedite_logistics",
        )
    except Exception as exc:
        return {
            "action": "manual_service",
            "error_code": "ticket_creation_failed",
            "error_message": str(exc),
            "response": "物流催办工单创建失败，请联系人工客服。",
        }
    
    return {
        "action": "expedite_logistics",
        "ticket_id": ticket.ticket_id,
        "response": (
            f"已为订单中的{product}创建物流催办工单"
            f" {ticket.ticket_id}。"
        ),
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

