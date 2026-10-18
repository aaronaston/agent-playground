#!/usr/bin/env python3
"""The smallest useful MCP server: a tool that takes a while and talks while it works,
and a tool that pushes a change notification to subscriptions/listen streams.

Run over Streamable HTTP on http://127.0.0.1:8000/mcp :
    uv run python server.py
Run over stdio instead:
    uv run python server.py stdio
"""
import asyncio
import sys

from mcp.server.mcpserver import Context, MCPServer

mcp = MCPServer(name="study-server", version="0.1.0")


@mcp.tool()
async def slow_count(n: int, ctx: Context) -> str:
    """Count to n, one second per step, reporting progress and logging as it goes."""
    await ctx.info(f"starting to count to {n}")
    for i in range(1, n + 1):
        await asyncio.sleep(1)
        await ctx.report_progress(i, n, message=f"at {i}")
        await ctx.info(f"reached {i}")
    return f"counted to {n}"


@mcp.tool()
async def announce_change(ctx: Context) -> str:
    """Pretend the tool set changed: pushes notifications/tools/list_changed to listeners."""
    await ctx.notify_tools_changed()
    return "notified listeners"


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.run(transport="streamable-http", host="127.0.0.1", port=8000, streamable_http_path="/mcp")
