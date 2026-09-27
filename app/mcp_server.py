from typing import Any

from mcp.server import MCPServer

from mcp.types import ToolAnnotations

from app.tools import (
    create_logistics_expedite_ticket_tool,
    create_refund_review_ticket_tool,
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

READ_ONLY_TOOL = ToolAnnotations(
    read_only_hint=True,
    open_world_hint=False,
)

IDEMPOTENT_WRITE_TOOL = ToolAnnotations(
    read_only_hint=False,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=False,
)

@mcp.tool(annotations=READ_ONLY_TOOL)
def get_order(order_id: str) -> dict[str, Any]:
    """根据订单号查询订单；处理售后请求前应先验证订单。"""
    return get_order_tool.invoke(
        {"order_id": order_id}
    )


@mcp.tool(annotations=READ_ONLY_TOOL)
def get_logistics(order_id: str) -> dict[str, Any]:
    """根据订单号查询物流状态和最新物流轨迹。"""
    return get_logistics_tool.invoke(
        {"order_id": order_id}
    )


@mcp.tool(annotations=READ_ONLY_TOOL)
def get_ticket_status(ticket_id: str) -> dict[str, Any]:
    """根据内部工单编号查询工单最新状态。"""
    return get_ticket_status_tool.invoke(
        {"ticket_id": ticket_id}
    )


@mcp.tool(annotations=READ_ONLY_TOOL)
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

@mcp.tool(annotations=IDEMPOTENT_WRITE_TOOL)
def create_logistics_expedite_ticket(
    order_id: str,
) -> dict[str, Any]:
    """为物流状态确认为 delayed 的订单创建或复用内部催办工单。"""
    return create_logistics_expedite_ticket_tool.invoke(
        {"order_id": order_id}
    )


@mcp.tool(annotations=IDEMPOTENT_WRITE_TOOL)
def create_refund_review_ticket(
    order_id: str,
) -> dict[str, Any]:
    """为有效订单创建或复用内部退款审核工单，不直接退款。"""
    return create_refund_review_ticket_tool.invoke(
        {"order_id": order_id}
    )