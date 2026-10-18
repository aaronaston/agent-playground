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
- `trace_session.py` – drives the running server by hand over raw TCP sockets, first as a 2026-07-28 client and then as a 2025-06-18 client, and narrates every byte: `→` lines are what the client sent, `←` lines are what the server sent with the time since the request, and each connection is numbered so you can see which request rode on which socket. Saves to `captures/streamable-http-session.txt`; commentary in `captures/streamable-http-session.annotated.md`.
- `transcripts/elicitation-two-ways.md` – a simulated HTTP/2 transcript of a tool call that needs user input, in the 2025 (server request on the stream) and 2026 (MRTR retry) styles. To be checked against a real capture in step 2.5.

## Run the capture yourself

```bash
uv run python server.py            # terminal 1
uv run python trace_session.py     # terminal 2; ~12 s
```

## Reading the trace

Each step has a banner saying what MCP call is being made and what to expect. Under it, the HTTP request the client wrote (every header, then the JSON-RPC body pretty-printed and labelled "request id=N method=..."), then the HTTP response as it arrived: status line and headers, then either a JSON body or, for a stream, each SSE event with a timestamp and its JSON-RPC payload labelled as a notification or a result. Connection lines (`[conn #N] opened` / `closed`) mark the TCP boundaries. Part A deliberately puts three requests on one connection; Part B opens a fresh connection per request.

## Notes so far

- The SDK answers both protocol families from one server with no configuration; it reads the family off each request.
- A `tools/list` in the 2026 family comes back as plain JSON. SSE only appears when the server has something to say before the result.
- Both `Mcp-Method` (2026) and `Mcp-Session-Id` (2025) are enforced with a 400.
- `ctx.info()` works but warns that the logging capability is deprecated as of 2026-07-28.
