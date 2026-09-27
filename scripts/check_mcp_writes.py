import asyncio

from mcp import Client

from app.mcp_server import mcp

async def main():
    async with Client(mcp) as client:
        logistics_first = await client.call_tool(
            "create_logistics_expedite_ticket",
            {"order_id": "ORD-1001"},
        )
        logistics_second = await client.call_tool(
            "create_logistics_expedite_ticket",
            {"order_id": "ORD-1001"},
        )

        return_first = await client.call_tool(
            "create_return_exchange_review_ticket",
            {"order_id": "ORD-1002"},
        )
        return_second = await client.call_tool(
            "create_return_exchange_review_ticket",
            {"order_id": "ORD-1002"},
        )

    print(
        "物流第一次：",
        logistics_first.structured_content,
    )
    print(
        "物流第二次：",
        logistics_second.structured_content,
    )
    print(
        "退换货第一次：",
        return_first.structured_content,
    )
    print(
        "退换货第二次：",
        return_second.structured_content,
    )

    assert logistics_first.is_error is False
    assert logistics_second.is_error is False
    assert return_first.is_error is False
    assert return_second.is_error is False

    assert (
        logistics_first.structured_content["ticket_id"]
        == logistics_second.structured_content["ticket_id"]
    )
    assert (
        return_first.structured_content["ticket_id"]
        == return_second.structured_content["ticket_id"]
    )

    print("MCP 写工具幂等验证通过")

if __name__ == "__main__":
    asyncio.run(main())