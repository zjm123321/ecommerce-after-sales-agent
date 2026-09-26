from langchain_core.tools import tool

from app.data import get_order
from app.logistics import get_logistics
from app.ticket_service import create_ticket


@tool
def get_order_tool(order_id: str) -> dict:
    """根据订单号查询订单信息。处理售后问题前，应先调用此工具确认订单是否存在。"""
    order = get_order(order_id)

    if order is None:
        return {
            "found": False,
            "order_id": order_id,
            "message": "订单不存在",
        }

    return {
        "found": True,
        "order_id": order_id,
        **order,
    }

@tool
def get_logistics_tool(order_id: str) -> dict:
    """根据订单号查询物流状态。判断是否需要催办物流前，必须调用此工具。"""
    logistics = get_logistics(order_id)

    if logistics is None:
        return {
            "found": False,
            "order_id": order_id,
            "message": "没有找到物流信息",
        }

    return {
        "found": True,
        "order_id": order_id,
        **logistics,
    }

@tool
def create_ticket_tool(
    order_id: str,
    issue_type: str,
    action: str,
) -> dict:
    """创建售后工单。只有确认订单和物流状态后，才能调用此工具。"""
    ticket = create_ticket(
        order_id=order_id,
        issue_type=issue_type,
        action=action,
    )

    return {
        "ticket_id": ticket.ticket_id,
        "order_id": ticket.order_id,
        "issue_type": ticket.issue_type,
        "action": ticket.action,
        "status": ticket.status,
    }