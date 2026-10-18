# Annotated: one MCP server, both protocol families, over Streamable HTTP (2026-10-18)

Raw capture: [`streamable-http-session.txt`](streamable-http-session.txt), produced by
`capture_session.sh` against `server.py` (mcp SDK 2.3.0, `MCPServer`, one tool
`slow_count` that logs and reports progress once a second). Everything is `curl -i -N`
over plain HTTP/1.1 to uvicorn on localhost, so there is no TLS, no ALPN and no HTTP/2;
the body framing is `Transfer-Encoding: chunked`.

The same server answered a 2026-07-28 client (Part A) and a 2025-06-18 client (Part B)
without configuration. The SDK picks the family from the request.

## Part A: 2026-07-28, stateless

**A1 `tools/list`.** No `initialize` first. The request carries protocol version, client
info, capabilities and log level in `params._meta`, and mirrors the method into the
`Mcp-Method` header. The server answered with **plain `application/json`**, 575 bytes,
no SSE at all: nothing to say mid-request, so no stream. The result has the 2026 fields
`resultType: "complete"` and `cacheScope: "private"`.

**A2 `tools/call slow_count(2)`.** Same headers plus `Mcp-Name: slow_count`, and a
`progressToken` in `_meta`. This time the server chose `text/event-stream`:

```
headers   content-type: text/event-stream, cache-control: no-cache, no-transform,
          x-accel-buffering: no, Transfer-Encoding: chunked
t=0.0s    notifications/message   "starting to count to 2"
t=1.0s    notifications/progress  1/2 "at 1"
          notifications/message   "reached 1"
t=2.0s    notifications/progress  2/2 "at 2"
          notifications/message   "reached 2"
          result id 2             content + structuredContent, resultType complete,
                                  _meta.serverInfo {study-server 0.1.0}
stream closed; curl: first byte 0.002 s, total 2.007 s
```

Every SSE event is `event: message`; no `id:` lines (no resumability in this family).
The notifications are only sent because the request's `_meta` carried
`io.modelcontextprotocol/logLevel`. First byte arrives immediately (the headers), then
the stream lives exactly as long as the tool runs.

**A3 `tools/list` with the `Mcp-Method` header omitted.** `400 Bad Request`, JSON-RPC
error `-32020` "mcp-method header does not match the request body's method". The
header-mirroring rule is enforced, not advisory.

## Part B: 2025-06-18, handshake and sessions

**B1 `initialize`.** Classic opening: `protocolVersion`, `capabilities`, `clientInfo` in
`params`. The server minted a session and returned it in the `mcp-session-id` response
header, and answered **over SSE** even though there was nothing to stream (one event,
then close). The result lists the server's capabilities and echoes `2025-06-18`.

**B2 `notifications/initialized`.** A notification, so `202 Accepted` with an empty
body. The session header is echoed back.

**B3 `tools/call slow_count(2)`.** Identical stream to A2, minus the 2026 fields:
no `resultType`, no `_meta.serverInfo` on the result. Progress and log notifications
look exactly the same in both families.

**B4 `tools/list` without the session header.** `400`, `-32600` "Missing session ID".
Note the server log: it created a transport for the request and immediately terminated
it. Sessions cost something even when rejected.

**B5 `GET` and `DELETE`.** The GET opened the 2025 standalone stream: `200`,
`text/event-stream`, and then silence until curl's 5-second timeout, because nothing
server-initiated happened. The DELETE ended the session with a `200`; the log shows
"Terminating session".

## What the server log added

Every `ctx.info(...)` call printed `MCPDeprecationWarning: The logging capability is
deprecated as of 2026-07-28 (SEP-2577)`. The SDK still sends the messages, but it is
telling you that per-request `notifications/message` is on its way out in favour of
stderr (stdio) or OpenTelemetry.

## Side by side

| | 2026-07-28 (A) | 2025-06-18 (B) |
|---|---|---|
| Opening | none; `_meta` on every request | `initialize` + `notifications/initialized` |
| Identity | `Mcp-Method`, `Mcp-Name` headers (enforced, A3) | `Mcp-Session-Id` header (enforced, B4) |
| `tools/list` response | plain JSON | SSE even for one event |
| Result fields | `resultType`, `cacheScope`, `_meta.serverInfo` | none of those |
| Progress / log on the call stream | identical | identical |
| Standalone server→client stream | gone (would be `subscriptions/listen`) | `GET` opens one |
| Ending | nothing to end | `DELETE` |

## Against the other captures

Next to the OpenAI Responses stream: same `text/event-stream`, same blank-line framing,
but here `event:` is always `message` and the type lives in the JSON-RPC `method`.
Next to `sse_server.py`: same shape as your own server, with `x-accel-buffering: no`
added for proxies and no `id:` because this family does not resume.
