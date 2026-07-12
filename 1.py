import asyncio

from amrita_core.tools.mcp import MCPClient


async def main():
    await MCPClient("http://192.168.1.25:9178/sse")._connect()


asyncio.run(main())
