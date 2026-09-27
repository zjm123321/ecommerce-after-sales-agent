import asyncio

from mcp import Client


async def main():
    async with Client(
        "http://127.0.0.1:8000/mcp"
    ) as client:
        tools = await client.list_tools()
        result = await client.call_tool(
            "get_order",
            {"order_id": "ORD-1001"},
        )

        print("协议版本：", client.protocol_version)
        print(
            "工具列表：",
            [tool.name for tool in tools.tools],
        )
        print("订单结果：", result.structured_content)

        assert result.is_error is False
        assert result.structured_content["found"] is True

    print("MCP Streamable HTTP 验证通过")


if __name__ == "__main__":
    asyncio.run(main())