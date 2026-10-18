# Protocol Notes: Streaming Foundations

These notes support Track B1 of the [study guide](../../STUDY_GUIDE.md). The examples are deliberately small: real deployments also depend on proxies, load balancers, clients, and application-level framing.

## Server-Sent Events (SSE)

SSE is a text-based, one-way event stream from server to client over an ordinary HTTP response. The response uses `Content-Type: text/event-stream`; the client can send requests in the usual way, but the open stream itself only carries server-to-client events.

An event is UTF-8 text terminated by a blank line. Fields are line-oriented:

```text
event: update
id: 7
data: {"status":"working"}

```

- `data:` carries the event data. Multiple `data:` lines are joined with newline characters.
- `event:` names the event; absent it, the event type is `message`.
- `id:` sets the last event ID. A reconnecting browser `EventSource` can send it back as `Last-Event-ID`.
- `retry:` can suggest a reconnect delay in milliseconds.
- A line starting with `:` is a comment, often used as a keep-alive.

The blank line matters: without it, the client has not received a complete event. SSE gives browsers a standard reconnecting `EventSource` API, but reconnecting does not itself guarantee replay; the server must retain and resend events if the application needs that behavior. `EventSource` reconnects automatically; generic clients such as curl do not.

### SSE and other streaming shapes

SSE is a defined event format on an HTTP response. Chunked transfer encoding is an HTTP/1.1 message-body framing mechanism, not an event format or a synonym for SSE. A server may send SSE data in HTTP chunks, but applications should not depend on chunk boundaries; HTTP/2 uses DATA frames instead of HTTP/1.1 chunked transfer encoding.

## WebSockets

For the protocol itself, byte by byte, see [`websockets-primer.md`](websockets-primer.md).

WebSockets establish a persistent connection that carries messages in both directions. A browser starts with a handshake over HTTP; after the upgrade, WebSocket frames carry text or binary messages as well as control frames such as ping, pong, and close. Both peers can send without creating a new HTTP request for every message.

Compared with SSE:

| | SSE | WebSockets |
|---|---|---|
| Direction | Server to client on the response | Bidirectional |
| Application data | Text event stream with standard fields | Framed text or binary messages; application defines message meaning |
| Browser API | `EventSource` (reconnect support) | `WebSocket` (reconnect is application-managed) |
| Typical fit | Notifications, generated text, server updates | Interactive, low-latency two-way sessions |

SSE is often simpler for token and status updates when the client mostly sends a request and then receives updates. WebSockets make sense when the client also needs frequent messages on the same live connection. A WebSocket connection still needs application-level decisions for authorization, heartbeats, retries, ordering across reconnects, and backpressure.

## HTTP/1.1 and HTTP/2

HTTP defines request/response semantics; HTTP/1.1 and HTTP/2 transport those semantics differently. A streaming response can be produced with either version.

- **Connection reuse:** HTTP/1.1 persistent connections can serve multiple requests in sequence. HTTP/2 also reuses a connection and allows many concurrent streams on it.
- **Multiplexing:** HTTP/2 interleaves frames from multiple streams over one connection. HTTP/1.1 responses on a connection are ordered; browsers commonly open several connections to a host to get concurrency.
- **Head-of-line blocking:** HTTP/1.1 pipelining can make later responses wait behind an earlier response. HTTP/2 avoids that HTTP-level response ordering between streams, but all streams on one HTTP/2 connection still share TCP: packet loss can stall data across streams until TCP recovers.
- **Streaming/framing:** HTTP/1.1 can use chunked transfer encoding when the body length is not known ahead of time. HTTP/2 uses DATA frames and does not use chunked transfer coding. Neither framing tells the application what an event means.
- **Flow control:** HTTP/2 has stream- and connection-level flow control. Applications and clients still need to consume data promptly and handle slow readers.

HTTP/2 multiplexing can reduce the need for parallel connections, but it does not eliminate latency, TCP loss effects, or server limits. HTTP/3 uses QUIC and changes the transport-level loss behavior; it is outside this warm-up.

### What `multiplex_demo.py` showed (2026-10-18, against httpbin.org)

| Demo | HTTP/1.1 | HTTP/2 |
|---|---|---|
| A: 4 parallel GETs | 4 TCP connections | 1 connection, streams 1, 3, 5, 7 |
| B: 8 × `/delay/2`, six-connection cap | two waves: 6 done at ~2.2 s, 2 more at ~4.2–4.5 s | one wave: all 8 done at ~2.1–2.4 s, streams 1–15 |
| C: `/delay/3` then `/get`, one connection | `/get` finished at ~3.3 s (queued behind the slow one) | `/get` finished at ~0.1 s while `/delay/3` was still open |

Why it matters here: every SSE stream holds a response open for its whole life. Over HTTP/1.1 that permanently consumes one of the browser's ~6 connections to that host, so a page with several live streams starves its other requests. Over HTTP/2 each stream is just another stream id on the one connection. Demo C is the mechanism: on HTTP/1.1 nothing else can use a connection while a response is in flight, and an SSE response is in flight indefinitely.

### Connection reuse does not mean backend affinity (`lb_demo/`, 2026-10-18)

| Path | Client connections | Where the four requests went |
|---|---|---|
| L7 proxy, HTTP/2 | 1 (streams 1, 3, 5, 7) | backend1, backend1, backend2, backend2 |
| L7 proxy, HTTP/1.1 keep-alive | 1 (reused three times) | backend2, backend1, backend2, backend1 |
| L4 proxy, HTTP/1.1 keep-alive | 1 (reused three times) | backend1 ×4 |
| L4 proxy, three new connections | 3 | backend2, backend1, backend2 |

A TCP (L4) load balancer forwards bytes, so one client connection maps to one backend connection for its life. An HTTP (L7) proxy terminates the client's connection, parses each request or HTTP/2 stream, and picks an upstream for it from a shared pool. nginx's default is round robin per request; the same holds for Envoy, HAProxy in HTTP mode, and cloud application load balancers. So "same connection" gives no affinity through an L7 proxy, and HTTP/2 does not change that: nginx cannot even speak HTTP/2 to upstreams here, so the client's one connection fans out into ordinary HTTP/1.1 upstream connections. Affinity has to be requested explicitly, by hashing on a cookie or header (which is why 2025 MCP put the session id in a header rather than only in the JSON body).

## Practical tradeoffs and pitfalls

- **Connection reuse and multiplexing:** Reuse avoids repeated setup. HTTP/2 can multiplex concurrent requests; SSE occupies an open response stream, while a WebSocket uses a long-lived upgraded connection.
- **Buffering:** Frameworks, reverse proxies, and CDNs may buffer output. Flush events on the server, use `curl -N` when inspecting, and configure intermediaries for streaming where needed. A client seeing delayed output does not prove the protocol itself buffers it.
- **Idle timeouts:** Proxies and load balancers may close quiet long-lived connections. SSE comment heartbeats or WebSocket ping/pong can help detect or prevent idle closure, but must fit intermediary timeout policies.
- **Direction:** SSE is a natural one-way server-to-client channel with ordinary HTTP requests in the other direction. WebSockets are natively bidirectional. Choose based on message patterns rather than assuming bidirectional is always better.
- **Failure and resume:** SSE has event IDs and a reconnection request convention, but replay is server behavior. WebSockets require the application to design reconnection and resume semantics.
- **Resource limits:** Long-lived connections consume server and intermediary resources. Consider per-client limits, cancellation, backpressure, and cleanup.

## Where these fit in the study

1. **LLM streaming (B1 / Rung 1):** Provider APIs commonly expose generated output and other response events over HTTP streaming, often using SSE. Inspect the provider's actual event schema; SSE framing is separate from the model/API event vocabulary.
2. **MCP (B2):** The current Streamable HTTP transport uses HTTP POST requests and may use SSE-formatted responses for server-to-client message streams. SSE is an option within that transport, not a replacement for MCP's JSON-RPC messages or transport rules. MCP also supports stdio. Check the current spec because transport details can evolve.
3. **A2A (B3):** A2A supports streaming task updates over SSE. Here too, SSE is the delivery mechanism; A2A defines the task and update semantics.

## References

- [WHATWG HTML: Server-sent events](https://html.spec.whatwg.org/multipage/server-sent-events.html) — event stream format, `EventSource`, reconnect behavior.
- [RFC 6455: The WebSocket Protocol](https://www.rfc-editor.org/rfc/rfc6455) — handshake, frames, control messages.
- [RFC 9112: HTTP/1.1](https://www.rfc-editor.org/rfc/rfc9112) — HTTP/1.1 message framing and connection management.
- [RFC 9113: HTTP/2](https://www.rfc-editor.org/rfc/rfc9113) — streams, frames, multiplexing, and flow control.
- [RFC 9110: HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110) — shared HTTP semantics.
- [MCP transport specification](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports) — stdio and Streamable HTTP.
- [A2A protocol specification](https://a2a-protocol.org/latest/specification/) — tasks, streaming, and protocol concepts.
- [OpenAI: Streaming API responses](https://platform.openai.com/docs/guides/streaming-responses) — provider-level streaming events.
- [Anthropic: Streaming Messages](https://docs.anthropic.com/en/api/messages-streaming) — Messages API event types and streaming behavior.

## Why SSE at all three layers (B1 checkpoint, draft 2026-10-18)

All three uses are the same shape: a client sends one request and the interesting part of the answer takes time to produce. An LLM response is tokens arriving over seconds; an MCP tool call may emit progress and log messages before its result; an A2A task reports status changes as it runs. In each case the client already made a request, so the natural channel is the response to it. SSE is the only standard way to put many framed messages into one HTTP response while staying HTTP: bearer tokens in headers, ordinary proxies and CDNs, one HTTP/2 stream per response rather than a dedicated connection, and the `fetch` API on the client. WebSockets would buy bidirectionality that none of the three layers needs per connection; the answers in the other direction are all sent as new requests (a tool result, an MRTR retry, an A2A message), which keeps servers stateless and lets any instance behind a load balancer take the follow-up. What SSE gives up, browser-native resume, turned out not to matter: the LLM APIs and the 2026 MCP revision both dropped `id:` lines and tell clients to re-issue the request.
