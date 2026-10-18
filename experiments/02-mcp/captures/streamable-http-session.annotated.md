# Annotated: an MCP 2026-07-28 session over Streamable HTTP (2026-10-18)

Raw trace: [`streamable-http-session.txt`](streamable-http-session.txt), produced by
`trace_session.py` against `server.py` (mcp SDK 2.3.0). The script opens the TCP
connections itself and labels every line `→` (client sent) or `←` (server sent, with
elapsed time), so direction and connection boundaries are explicit. Plain HTTP/1.1 to
uvicorn on localhost: no TLS, no HTTP/2; streamed bodies use chunked encoding.

This protocol version has **no handshake and no sessions**. Every request carries the
protocol version, client identity and capabilities in `params._meta`, and mirrors its
method into the `Mcp-Method` header so proxies can route without parsing JSON.

## Part 1: discovery, listing, a streamed call. One connection, three requests.

**1 `server/discover`.** Optional, and the only thing resembling an opening. Plain JSON
back: the server's capabilities, `supportedVersions: ["2026-07-28"]`, its identity in
`_meta.serverInfo`, and the 2026 result fields `resultType: "complete"`, `cacheScope`,
`ttlMs`. A client can call this first to choose a version, or skip it and just send
requests.

**2 `tools/list`.** Plain JSON again, 575 bytes: two tools with `inputSchema` and
`outputSchema`. Nothing to say mid-request, so no stream.

**3 `tools/call slow_count(2)`** with `Mcp-Name: slow_count` and a `progressToken`.
Now the server chose `text/event-stream`:

```
+0.001s  headers: text/event-stream, cache-control: no-cache, no-transform, x-accel-buffering: no, chunked
+0.001s  #1 notifications/message   "starting to count to 2"
+1.003s  #2 notifications/progress  1/2 "at 1"
+1.004s  #3 notifications/message   "reached 1"
+2.006s  #4 notifications/progress  2/2 "at 2"
+2.006s  #5 notifications/message   "reached 2"
+2.007s  #6 result id=3             content + structuredContent, resultType complete, _meta.serverInfo
+2.007s  end of chunked body; the response is over
```

Every SSE event is `event: message`; the type is the JSON-RPC `method`. No `id:` lines:
this version has no stream resumability. The log messages are only sent because the
request's `_meta` carried `io.modelcontextprotocol/logLevel`. All three requests rode
one keep-alive connection, which the client then closed.

## Part 2: what the server rejects

| Step | Request | Response |
|---|---|---|
| 4a | `tools/list` without `Mcp-Method` | `400`, JSON-RPC error `-32020` HeaderMismatch |
| 4b | `tools/list` claiming version `2027-01-01` | `400`, `-32022` UnsupportedProtocolVersion, `data.supported: ["2026-07-28"]` |
| 4c | `GET` on the endpoint | `405 Method Not Allowed`: the 2025 standalone stream no longer exists |

4b is the whole of version negotiation in this protocol: ask for what you want, get told
what exists, try again.

## Step 5: `subscriptions/listen`, the only long-lived stream

The modern replacement for the 2025 GET stream, and the only way the server can send
something the client did not just ask for. It is an ordinary POST whose response stream
stays open.

```
conn #5  → POST subscriptions/listen  {notifications: {toolsListChanged: true}}
         ← +0.002s  200, text/event-stream
         ← +0.002s  notifications/subscriptions/acknowledged
                    params.notifications {toolsListChanged: true}
                    params._meta.subscriptionId = 5   (the JSON-RPC id of the listen request)
         ← +2.002s  (quiet; nothing has happened)
conn #6  → POST tools/call announce_change            ← 200, plain JSON result
         (the tool calls notify_tools_changed() on the server)
conn #5  ← +2.006s  notifications/tools/list_changed, tagged with subscriptionId 5
         ← +4.007s  (quiet again)
client closes conn #5: that is how you unsubscribe
```

Things to notice: the client opted in to one notification type and the acknowledgement
echoes exactly what the server agreed to send; the notification arrived on the listen
stream, not on conn #6's response, because it is unrelated to that request; and the
request-scoped messages from step 3 (progress, log) would never appear here. Closing the
stream is the unsubscribe; there is no message for it.

## Summary of the wire

Six TCP connections, every one opened by the client. Eight HTTP requests. Two SSE
streams: the slow tool call (notifications before its result) and the listen channel.
Everything else was a single JSON object. The server never initiated a connection,
never sent a request to the client, and kept no state between requests.

## Appendix: the 2025-06-18 handshake family

`trace_session.py --legacy` appends steps L1–L6 against the same server, which answers
both families without configuration. The differences you will see: an `initialize`
request first, whose response mints an `Mcp-Session-Id` header that must be echoed on
everything after (omit it: `400 -32600 Missing session ID`); `notifications/initialized`
answered with `202`; the same progress and log stream on the tool call but no
`resultType` or `_meta.serverInfo` on the result; a `GET` that opens a standalone
stream and sits silent; and `DELETE` to end the session. Useful for recognising an
older server in the wild, not for learning the protocol.

## Against the other captures

Next to the OpenAI Responses stream in `00-protocols`: same `text/event-stream`, same
blank-line framing, but here `event:` is always `message` and the type lives in the
JSON-RPC `method`. Next to `sse_server.py`: same shape as your own server, with
`x-accel-buffering: no` added for proxies and no `id:` because this version does not
resume.
