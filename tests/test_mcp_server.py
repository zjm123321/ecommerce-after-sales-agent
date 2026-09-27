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