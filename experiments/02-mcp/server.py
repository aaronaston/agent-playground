#!/usr/bin/env python3
"""The smallest useful MCP server: a tool that takes a while and talks while it works,
and a tool that pushes a change notification to subscriptions/listen streams.

Run over Streamable HTTP on http://127.0.0.1:8000/mcp (PORT=8001 to change):
    uv run python server.py
Run over stdio instead:
    uv run python server.py stdio
"""
import asyncio
import os
import sys

from pydantic import BaseModel, Field

from typing import Annotated

from mcp.server.mcpserver import Context, Elicit, MCPServer, RequestStateSecurity, Resolve

# request_state_security lets the server hand its position to the client, sealed,
# when it needs more input (MRTR). ephemeral() = a key that lives only in this process.
mcp = MCPServer(name="study-server", version="0.1.0",
                request_state_security=RequestStateSecurity.ephemeral())

FAKE_WEATHER = {"toronto": "11 °C, overcast, light wind", "vancouver": "14 °C, rain"}


class CityAnswer(BaseModel):
    city: str = Field(description="City name")


@mcp.tool()
async def slow_count(n: int, ctx: Context) -> str:
    """Count to n, one second per step, reporting progress and logging as it goes."""
    await ctx.info(f"starting to count to {n}")
    for i in range(1, n + 1):
        await asyncio.sleep(1)
        await ctx.report_progress(i, n, message=f"at {i}")
        await ctx.info(f"reached {i}")
    return f"counted to {n}"


def ask_city() -> Elicit[CityAnswer]:
    """Resolver: the framework turns this into an elicitation. Under 2026-07-28 that means
    the call returns an input_required result and resumes when the client retries."""
    return Elicit("Weather for which city?", CityAnswer)


@mcp.tool()
async def weather(ctx: Context, city: Annotated[CityAnswer, Resolve(ask_city)]) -> str:
    """Current weather. Always asks the user which city they mean."""
    await ctx.info(f"looking up {city.city}")
    return f"{city.city}: {FAKE_WEATHER.get(city.city.lower(), 'no data for that city')}"


@mcp.tool()
async def announce_change(ctx: Context) -> str:
    """Pretend the tool set changed: pushes notifications/tools/list_changed to listeners."""
    await ctx.notify_tools_changed()
    return "notified listeners"


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.run(transport="streamable-http", host="127.0.0.1", port=int(os.environ.get("PORT", "8000")),
                streamable_http_path="/mcp")
