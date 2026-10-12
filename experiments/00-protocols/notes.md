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
