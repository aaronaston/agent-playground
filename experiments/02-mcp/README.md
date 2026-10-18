# 02 – MCP: the protocol and its features

Hands-on for **Track B2** of the [study guide](../../STUDY_GUIDE.md), Part 2 of the
[walkthrough](../../WALKTHROUGH.md). Python SDK `mcp` 2.x (`MCPServer`, formerly FastMCP).

## Setup

```bash
cd experiments/02-mcp
uv sync
```

## What is here

- `server.py` – the smallest useful server: one tool, `slow_count(n)`, that logs and reports progress once a second. `uv run python server.py` serves Streamable HTTP on `http://127.0.0.1:8000/mcp`; add `stdio` to speak stdio instead.
- `capture_session.sh` – drives the running server with curl as a 2026-07-28 client and then as a 2025-06-18 client, saving every header and byte to `captures/streamable-http-session.txt`. Annotated in `captures/streamable-http-session.annotated.md`.
- `transcripts/elicitation-two-ways.md` – a simulated HTTP/2 transcript of a tool call that needs user input, in the 2025 (server request on the stream) and 2026 (MRTR retry) styles. To be checked against a real capture in step 2.5.

## Run the capture yourself

```bash
uv run python server.py            # terminal 1
./capture_session.sh               # terminal 2; ~15 s
```

## Notes so far

- The SDK answers both protocol families from one server with no configuration; it reads the family off each request.
- A `tools/list` in the 2026 family comes back as plain JSON. SSE only appears when the server has something to say before the result.
- Both `Mcp-Method` (2026) and `Mcp-Session-Id` (2025) are enforced with a 400.
- `ctx.info()` works but warns that the logging capability is deprecated as of 2026-07-28.
