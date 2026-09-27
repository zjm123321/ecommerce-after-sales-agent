import asyncio

from mcp import Client

from app.mcp_server import mcp


def test_mcp_lists_expected_read_only_tools():
    async def run_test():
        async with Client(mcp) as client:
            result = await client.list_tools()
            return {tool.name for tool in result.tools}

    tool_names = asyncio.run(run_test())

    assert tool_names == {
        "get_order",
        "get_logistics",
        "get_ticket_status",
        "search_refund_policy",
        "create_logistics_expedite_ticket",
        "create_refund_review_ticket",
    }


def test_mcp_get_order():
    async def run_test():
        async with Client(mcp) as client:
            return await client.call_tool(
                "get_order",
                {"order_id": "ORD-1001"},
            )

    result = asyncio.run(run_test())

    assert result.is_error is False
    assert result.structured_content["found"] is True
    assert result.structured_content["order_id"] == "ORD-1001"
    assert result.structured_content["product"] == "蓝牙耳机"


def test_mcp_get_missing_order():
    async def run_test():
        async with Client(mcp) as client:
            return await client.call_tool(
                "get_order",
                {"order_id": "ORD-9999"},
            )

    result = asyncio.run(run_test())

    assert result.is_error is False
    assert result.structured_content == {
        "found": False,
        "order_id": "ORD-9999",
        "message": "订单不存在",
    }


def test_mcp_get_logistics():
    async def run_test():
        async with Client(mcp) as client:
            return await client.call_tool(
                "get_logistics",
                {"order_id": "ORD-1002"},
            )

    result = asyncio.run(run_test())

    assert result.is_error is False
    assert result.structured_content["found"] is True
    assert result.structured_content["status"] == "delivered"

def test_mcp_tool_annotations():
    async def run_test():
        async with Client(mcp) as client:
            result = await client.list_tools()
            return {
                tool.name: tool
                for tool in result.tools
            }

    tools = asyncio.run(run_test())

    assert tools["get_order"].annotations.read_only_hint is True
    assert (
        tools["search_refund_policy"]
        .annotations.read_only_hint
        is True
    )

    logistics_write = tools[
        "create_logistics_expedite_ticket"
    ]
    assert (
        logistics_write.annotations.read_only_hint
        is False
    )
    assert (
        logistics_write.annotations.destructive_hint
        is False
    )
    assert (
        logistics_write.annotations.idempotent_hint
        is True
    )


def test_mcp_rejects_expedite_for_delivered_order():
    async def run_test():
        async with Client(mcp) as client:
            return await client.call_tool(
                "create_logistics_expedite_ticket",
                {"order_id": "ORD-1002"},
            )

    result = asyncio.run(run_test())

    assert result.is_error is False
    assert result.structured_content == {
        "created": False,
        "order_id": "ORD-1002",
        "reason": "物流状态不是延迟，不能创建催办工单",
    }


def test_mcp_rejects_refund_for_missing_order():
    async def run_test():
        async with Client(mcp) as client:
            return await client.call_tool(
                "create_refund_review_ticket",
                {"order_id": "ORD-9999"},
            )

    result = asyncio.run(run_test())

    assert result.is_error is False
    assert result.structured_content == {
        "created": False,
        "order_id": "ORD-9999",
        "reason": "订单不存在",
    }