# Questions log

Probing questions asked along the way, the distilled answer, and what changed in the walkthrough as a result. Newest at the bottom. The full discussion lives in the chat; this is the residue worth keeping.

Format: **Q** · **A** (a few lines) · **Changed** (what moved in WALKTHROUGH.md or STUDY_GUIDE.md, or "nothing").

---

## 2026-10-17

**Q: Is SSE just a formalisation of the old DHTML "keep the connection open and push script tags" trick?**
**A:** Yes, in architecture. What it adds: a data format instead of executable payloads, a browser-native client (`EventSource`), and resumable reconnection via `id:` / `Last-Event-ID`. Inherited warts: text-only, one direction, proxies that buffer, `:` keepalive comments as padding. Over HTTP/1.1 each stream costs a connection against the ~6-per-host cap; HTTP/2 multiplexing dissolves that.
**Changed:** nothing.

**Q: Does my `sse_server.py` really support resume? It sends the same events every time.**
**A:** Mechanically yes (`Last-Event-ID: 3` yields 4..6, `Last-Event-ID: 6` yields 204). But the stream is a fixed script, so "skip ahead" and "replay" are indistinguishable. Real resume needs events produced independently of connections, global monotonic ids, a bounded replay buffer, and a "too far behind, resync" signal.
**Changed:** step 1.2 marked done with the limitation noted. Possible later exercise: background ticker + shared log.

**Q: What does a reconnect look like on the wire? Where does `Last-Event-ID` go?**
**A:** A plain new GET with one extra request header. Everything in the event-stream body is server→client (`data`, `event`, `id`, `retry`); `Last-Event-ID` is the client's only word. `EventSource` cannot set custom headers, which is why SDKs use `fetch` and parse `text/event-stream` themselves.
**Changed:** nothing.

**Q: Why did MCP choose SSE? Where does the tool call go? Is it POST-then-SSE?**
**A:** Yes: one endpoint, every client message is a POST, the response is either `application/json` or a `text/event-stream` ending with the JSON-RPC result. SSE exists because MCP is bidirectional JSON-RPC: progress, log messages, and (in 2025 revisions) server→client requests must arrive *before* the result. Tool results themselves are never streamed token by token. The 2024-11-05 HTTP+SSE transport (GET `/sse` first, replies on a different connection) is the design that didn't make sense; Streamable HTTP fixed it. Not WebSockets: keeps bearer headers, proxies, serverless, HTTP/2.
**Changed:** nothing.

**Q: What are all the MCP message types? And isn't a JSON-RPC notification an odd way to send an event?**
**A:** 2025-06-18 has 25 methods (see STUDY_GUIDE B2.2 exercise). A notification is a request without an `id`; strip the vocabulary and it is `{type, data}`. The `notifications/` prefix is the spec admitting it. The RPC costume buys one envelope, bidirectional symmetry, and LSP precedent. Correlation glue: `progressToken` and `requestId`.
**Changed:** nothing.

**Q: Is 2024-11-05 an MCP version? Has the protocol changed dramatically? What is Streamable HTTP?**
**A:** Versions are date-named: 2024-11-05, 2025-03-26, 2025-06-18, 2025-11-25, 2026-07-28. Two dramatic changes: 2025-03-26 (HTTP+SSE → Streamable HTTP) and 2026-07-28 (stateless: no sessions, no `initialize`, no GET stream, no resumability; MRTR replaces server-initiated requests; Sampling/Roots/Logging deprecated). "Streamable HTTP" = plain POST where the response *may* be an SSE stream; SSE is an ingredient, not an alternative.
**Changed:** STUDY_GUIDE B2 rewritten as a full module against 2026-07-28; B2 moved ahead of Rung 1 chatbots in the suggested order. Walkthrough Part 2 created from it.

**Q: Why "any of the last three" versions? Are old ones decommissioned?**
**A:** Loose phrasing on my part. Nothing is decommissioned; the Python SDK supports all five, with 2024-11-05 as oldest. The SDK's real split is "handshake" (2024–2025) vs "modern" (2026-07-28). Deprecation applies to features (12-month window), not versions.
**Changed:** B2.1 wording in STUDY_GUIDE.

**Q: `compare_http.py` fails with 502.**
**A:** The nghttp2.org httpbin backend is down; its front-end still negotiated h2 and h1.1 fine, which is itself the lesson: ALPN settles the version before any request is sent. Switched the default to `httpbin.org/stream/5`.
**Changed:** step 1.3 gained the "why a 502 still reported HTTP/2" done-when.

**Q: What is httpbin.org? Why `/stream/5`?**
**A:** Public HTTP echo/test service (Kenneth Reitz, now hosted by Postman). `/stream/5` sends five JSON lines as a chunked response, so it exercises body framing differences between HTTP/1.1 and HTTP/2. It is not SSE. `/drip` is better for watching bytes arrive over time.
**Changed:** step 1.3 now includes a `drip` call.

## 2026-10-18

**Q: I'm "failing" step 1.3. I see the version requested and served, and slightly different status lines, but no significant differences.**
**A:** Correct diagnosis: the exercise was wrong, not the observation. One request per protocol can only show which version ALPN negotiated. The real differences are properties of many requests sharing a connection: HTTP/1.1 needs one connection per concurrent request and serialises responses on each; HTTP/2 multiplexes streams on one connection. Observed with `curl -Z`: 4 connections vs 1; eight 2-second requests in two waves (2 s, 4 s) under a six-connection cap vs one wave; a fast request stuck behind a slow one for 3.3 s vs finishing at 0.1 s.
**Changed:** new script `experiments/00-protocols/experiments/multiplex_demo.py`; step 1.3 rewritten around it; observed numbers recorded in notes.md. Lesson for writing future steps: a "look for" must name an observable that differs, not just a command to run.

**Q: Why is it called the "Comet era"?**
**A:** A pun on Ajax: both are scouring-powder brands. Jesse James Garrett coined Ajax (2005) for client-pull; Alex Russell coined Comet (2006) for server-push over held-open HTTP. Umbrella term for long polling, forever-frame, XHR streaming. The era ends when `EventSource` (HTML5, ~2009–2011) and WebSockets (RFC 6455, Dec 2011) gave browsers native push. Early browsers allowed two connections per host, which is why the cap in demo B mattered so much.
**Changed:** nothing.

**Q: Why are the HTTP/2 stream IDs odd numbers only?**
**A:** RFC 9113 uses parity to say who opened the stream: client-initiated are odd, server-initiated are even, each side counts upward independently so no coordination is needed. Stream 0 is the connection itself. Even streams exist only for server push, which is effectively dead (Chrome removed it in 2022), so in practice you only see odd. IDs start at 1 over TLS/ALPN (an h2c upgrade would consume 1 implicitly and start at 3), never reset, and exhausting the 31-bit space forces a new connection.
**Changed:** nothing.

**Q: Can we visualise the HTTP/1.1 vs HTTP/2 run instead of reading a text timeline?**
**A:** Yes. `multiplex_demo.py --json` now records per-transfer phase timings (connect, TLS, first byte, total) and curl's `conn_id`; `multiplex_viz.py` renders them as a Gantt-style timeline, lanes per TCP connection, both protocols on one axis per demo. Reuse shows up as a bar with no handshake segments; head-of-line blocking as a short bar that cannot start until the long one ends.
**Changed:** step 1.3 now includes the visualisation; two new scripts.

**Q: Is HTTP/1.1-based Streamable HTTP simplex and HTTP/2-based duplex? How does a client send while the server is streaming, and how does it answer a server request?**
**A:** Neither is simplex; TCP is duplex underneath both. HTTP/1.1 is half-duplex *per connection at the message level*: one request, then one response, and a connection streaming a response cannot carry another request. So an MCP client's next message is simply another POST on another connection (or an idle one from the pool). HTTP/2 has the same request/response rule per *stream*; the streams just share one connection. MCP's design is identical on both: every client→server message is a new HTTP request; the "duplex" is concurrency of requests, not two-way use of one response. A 2025-style server request (sampling, elicitation) arrives on a response stream; the client answers by POSTing a JSON-RPC *response* to the same endpoint, which the server acknowledges with 202, then continues the original stream. That cross-connection correlation needs server state (sessions, sticky routing), which is what 2026-07-28 removed by replacing server-initiated requests with MRTR retries.
**Changed:** nothing in the steps; worth folding into B2.3 notes when reached.

**Q: Show me a simulated HTTP/2 transcript of an MCP tool call where the server asks for input (`input_required`) while the original request keeps working and logging.**
**A:** Written out in `experiments/02-mcp/transcripts/elicitation-two-ways.md`. Correction to the premise: under 2026-07-28 MRTR, `input_required` is a *result*, so the stream closes and the server stops; the client retries the whole call (new id, same params, plus `inputResponses` and an echoed `requestState`) and the work happens in the second exchange. The "keep working while waiting" shape is the 2025 pattern: the server sends an `elicitation/create` *request* on the open stream, the client POSTs a JSON-RPC *response* and gets a 202, and the original stream continues to the result. The table at the end of the file lists the trade-offs.
**Changed:** created `experiments/02-mcp/` early with this transcript; step 2.5 should compare a real capture against it.


**Q: I don't understand the conclusion. Isn't Streamable HTTP on HTTP/2 the best experience?**
**A:** Two axes were being conflated. HTTP/1.1 vs HTTP/2 decides connection cost (the multiplex demo); both transcripts run identically on either. 2025 server-initiated requests vs 2026 MRTR decides whether the server may ask mid-stream and keep working or must stop and be re-asked; both are Streamable HTTP. The conclusion compared the second axis only. HTTP/2 does not rescue the 2025 pattern's routing problem, because load balancers terminate HTTP/2 at the edge and route per request, so two streams on one client connection can reach different instances. Summary: HTTP/2 makes the conversation cheaper, MRTR makes the server simpler; you want both.
**Changed:** nothing.

**Q: What is MRTR?**
**A:** Multi Round-Trip Requests, introduced in MCP 2026-07-28. One request may take several round trips: the server returns `resultType: "input_required"` with `inputRequests` and an opaque `requestState`; the client retries the same request with `inputResponses` and the echoed state; repeat until `resultType: "complete"`. Mandatory replacement for server-initiated `elicitation/create`, `sampling/createMessage`, and `roots/list`. Every exchange is self-contained; state travels through the client.
**Changed:** nothing (already in the glossary and transcript A).

**Q: Would a load balancer really route requests on one reused TCP connection to different backends? Isn't one TCP connection always one backend?**
**A:** Depends on the layer, and the demo in `experiments/00-protocols/experiments/lb_demo/` shows both. An L4 (TCP) balancer: yes, one client connection → one backend for its life. An L7 (HTTP) proxy, which is what nginx, Envoy, HAProxy-in-http-mode and cloud ALBs are: no. It terminates the client connection and picks an upstream per request (or per HTTP/2 stream) from a shared pool; nginx round-robin sent four requests on one HTTP/2 connection to both backends, and alternated per request on one HTTP/1.1 keep-alive connection. Affinity must be asked for (cookie/header hashing), which is why the 2025 MCP session id is a header.
**Changed:** step 1.3 gained an optional Docker demo; new table in notes.md.

