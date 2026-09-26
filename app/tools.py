from langchain_core.tools import tool

from app.data import get_order


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