import asyncio

from mcp import Client

from app.mcp_server import mcp


async def main():
    async with Client(mcp) as client:
        first = await client.call_tool(
            "create_logistics_expedite_ticket",
            {"order_id": "ORD-1001"},
        )
        second = await client.call_tool(
            "create_logistics_expedite_ticket",
            {"order_id": "ORD-1001"},
        )

    print("第一次：", first.structured_content)
    print("第二次：", second.structured_content)

    assert first.is_error is False
    assert second.is_error is False
    assert first.structured_content["created"] is True
    assert (
        first.structured_content["ticket_id"]
        == second.structured_content["ticket_id"]
    )

    print("MCP 写工具幂等验证通过")


if __name__ == "__main__":
    asyncio.run(main())