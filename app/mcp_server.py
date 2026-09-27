from typing import Any

from mcp.server import MCPServer

from app.tools import (
    get_logistics_tool,
    get_order_tool,
    get_ticket_status_tool,
    search_refund_policy_tool,
)


mcp = MCPServer(
    "ecommerce-after-sales",
    title="电商售后工具服务",
    description=(
        "以 MCP 协议提供订单、物流、工单和售后政策查询能力。"
    ),
)


@mcp.tool()
def get_order(order_id: str) -> dict[str, Any]:
    """根据订单号查询订单；处理售后请求前应先验证订单。"""
    return get_order_tool.invoke(
        {"order_id": order_id}
    )


@mcp.tool()
def get_logistics(order_id: str) -> dict[str, Any]:
    """根据订单号查询物流状态和最新物流轨迹。"""
    return get_logistics_tool.invoke(
        {"order_id": order_id}
    )


@mcp.tool()
def get_ticket_status(ticket_id: str) -> dict[str, Any]:
    """根据内部工单编号查询工单最新状态。"""
    return get_ticket_status_tool.invoke(
        {"ticket_id": ticket_id}
    )


@mcp.tool()
def search_refund_policy(
    order_id: str,
    query: str,
) -> dict[str, Any]:
    """根据已验证订单的真实状态检索适用退款政策。"""
    return search_refund_policy_tool.invoke(
        {
            "order_id": order_id,
            "query": query,
        }
    )