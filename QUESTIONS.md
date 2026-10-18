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


**Q: How do L7 load balancers actually work? Do they hold client connections, hold origin connections, change protocols between them, and how is an HTTP/2 upstream connection ever "available"?**
**A:** An L7 proxy is an HTTP server facing clients glued to an HTTP client facing origins; what crosses the middle is a request (method, headers, body stream), never a connection. Downstream protocol is negotiated with the client; upstream protocol is configured per backend; any combination (h2 in, h1.1 out is common; nginx only speaks h1.1 upstream). Upstream pool for HTTP/1.1: idle keep-alive connections, one request per connection at a time. For HTTP/2: one or few connections per backend, "available" means under the backend's max-concurrent-streams budget. Bodies stream through, so an SSE response pins one upstream connection or stream for its life. Routing is per request on headers, not the body (hence `Mcp-Method`, `Mcp-Name`, and the 2025 session header). Nothing from the client connection survives unless written into headers like `X-Forwarded-For`.
**Changed:** nothing. Possible follow-up: log the proxy's source port in `lb_demo/backend.py` to see the fan-out.

**Q: What is ALPN?**
**A:** Application-Layer Protocol Negotiation (RFC 7301), a TLS extension. The client lists protocols it can speak in its ClientHello (`h2`, `http/1.1`), the server names its pick in the ServerHello, and the chosen protocol starts as soon as the handshake ends. Per connection, before any request, which is why a failed request still reported HTTP/2. Created because HTTP/2 over TLS has no upgrade step. An L7 proxy does ALPN with the client; the origin is not involved. Plaintext HTTP/2 (`h2c`) has no ALPN, hence `--http2-prior-knowledge`. Check with `openssl s_client -alpn h2,http/1.1 -connect host:443`.
**Changed:** nothing.

**Q: Is there a primer on WebSockets? I don't know much about them.**
**A:** Written: `experiments/00-protocols/websockets-primer.md`, built around the repo's hand-rolled echo server and a new `ws_handshake.py` that prints real bytes. Core: an HTTP/1.1 GET with `Upgrade: websocket` gets a `101 Switching Protocols`, after which the socket carries framed messages both ways and is no longer HTTP. Frames have a 2-byte header (FIN, opcode, MASK, length); client frames are XOR-masked to defeat proxy cache poisoning; ping/pong/close are control frames; no reconnect or replay in the browser API. Over HTTP/2 needs RFC 8441, so most WebSockets still cost a dedicated HTTP/1.1 connection; through an L7 proxy they become a pinned byte pipe.
**Changed:** step 1.4 now points at the primer and the new script.

**Q: I have an OpenAI key in `experiments/.env`. Can we switch providers for step 1.5?**
**A:** Yes; the step is about seeing a real LLM SSE stream and the Responses API streams the same way. The key in the file was missing its leading `s` (`k-proj-...`), which the 401 message made visible; restored it. Capture and annotation are in `experiments/00-protocols/experiments/captures/`. Notable: `event:` names the type (unlike MCP), `sequence_number` instead of `id:`, an `obfuscation` padding field against token-length side channels, usage only in `response.completed`.
**Changed:** step 1.5 reworded to "LLM API stream" and marked done; the script now targets OpenAI and reads the shared `experiments/.env`.


**Q: So the Streamable HTTP changes bring MCP in line with what streaming LLM calls already did?**
**A:** Yes. Both are now: one POST, response is JSON or an SSE stream scoped to that request, terminal event ends it, no resume (re-issue), ordering in the payload, no server state beyond a server-minted handle (`previous_response_id` / `requestState`), long work via background-plus-poll (tasks extension). MRTR is function calling: the response ends saying "I need X", the client sends a new request with X. The 2025 transport did the architectural step; 2026 removed sessions, the GET stream and resumability. Remaining differences: MCP keeps a push channel (`subscriptions/listen`) where LLM APIs use webhooks, and MCP's envelope is JSON-RPC inside `event: message` rather than named events.
**Changed:** nothing.

**Q: Can you show a capture with a tool call?**
**A:** `experiments/00-protocols/experiments/captures/openai-tool-call-stream.txt`, with annotation. Exchange 1's stream ends with `status: completed` and a `function_call` item (`get_weather`, `call_id`), the arguments streamed in five deltas. The client runs the tool. Exchange 2 resends the user message, the function_call item, and a `function_call_output` keyed by `call_id`; the model answers in text. Two independent HTTP exchanges, input tokens 48 → 91. This is MRTR with the roles mirrored: here the model asks the client to run a tool; in MCP the server asks the client for input.
**Changed:** step 1.5 notes the second capture; step 2.5 should compare it with the MRTR transcript.

**Q: (step 1.6) Build the smallest MCP server and capture a Streamable HTTP session.**
**A:** Done with mcp SDK 2.3.0 (`MCPServer`; FastMCP is gone in 2.x). One server answered a 2026-07-28 client and a 2025-06-18 client without configuration. `tools/list` returned plain JSON; the slow tool call returned SSE with log and progress notifications once a second before the result; `event:` always `message`, no `id:` lines. Missing `Mcp-Method` → 400 `-32020`; missing `Mcp-Session-Id` (2025) → 400 `-32600`. The 2025 GET opened a silent standalone stream; DELETE ended the session. `ctx.info()` emits a deprecation warning citing SEP-2577.
**Changed:** 1.6, B1 checkpoint and 2.4 marked done; 2.2 in progress; root README renumbered (02 is now MCP, Anthropic moves to 03); `experiments/02-mcp/` has a README, `server.py`, `capture_session.sh`.


**Q: What is `uv`?**
**A:** Astral's Rust-based Python package and project manager (2024), replacing pip, venv, pip-tools and pyenv in one fast binary. `pyproject.toml` declares wants; `uv.lock` pins the exact resolved set so `uv sync` reproduces the environment; `uv run` executes inside the project venv without activation. Node mapping: package.json / package-lock.json / npm install / npm ci. Already the repo's convention; installed via Homebrew.
**Changed:** nothing.

**Q: Running 1.6, I can't tell which messages are from the client and which from the server, or how many connections there are. The trace isn't enough.**
**A:** Agreed; the curl-based capture had no narration. Replaced it with `experiments/02-mcp/trace_session.py`, which opens the sockets itself and prints: a banner per step naming the MCP call and the expectation; the full HTTP request with `→` on every line and the JSON-RPC body labelled ("request id=1 method=tools/list"); the response with `←` on every line, a timestamp on the status line and on each SSE event, and each payload labelled as a notification, result or error; and `[conn #N] opened/closed` lines. Part A rides three requests on one connection; Part B opens one per request; the summary counts them (7).
**Changed:** `capture_session.sh` removed; README, annotation and step 1.6 point at the trace script. Lesson for future steps: a capture must show direction, timing and connection boundaries, or it is not a capture the reader can learn from.

**Q: Can we do all of this on the latest MCP version only? I want to understand 2026-07-28 well first.**
**A:** Yes. `trace_session.py` is now 2026-07-28 only by default: `server/discover`, `tools/list`, a streamed `tools/call`, the three rejections (missing `Mcp-Method` → `-32020`, unknown version → `-32022` with the supported list, `GET` → `405`), and `subscriptions/listen` with a real `tools/list_changed` arriving on it after a trigger from another connection (new `announce_change` tool). The 2025 handshake family is behind `--legacy`. Six connections, eight requests, two streams, no handshake, no sessions.
**Changed:** step 2.1 reworded to "current spec first, changelog once for context"; Part 2 intro and STUDY_GUIDE B2 intro say latest first; annotation rewritten modern-first with a legacy appendix.

**Q: Can we extend the example with something that needs user input? "Tell me the weather" → "for which city?" → "Toronto".**
**A:** Done as trace step 6 with a `weather` tool. In the 2.x SDK, `ctx.elicit()` fails on this transport ("no back-channel"); the MRTR way is a parameter `Annotated[CityAnswer, Resolve(ask_city)]` whose resolver returns `Elicit("Weather for which city?", CityAnswer)`. On the wire: 6a returns plain JSON with `resultType: input_required`, `inputRequests["__main__:ask_city"]` = an `elicitation/create` with a form schema, and a 351-char sealed `requestState`; 6b retries the same call with `inputResponses` and the state and gets "Toronto: 11 °C…" after a log line; 6c with one character of state changed is refused (`-32602`); 6d with `action: decline` is a 200 with `isError: true`. The client must declare `elicitation.form` in its capabilities or the server may not ask.
**Changed:** step 2.5 half done; README and annotation extended; the simulated transcript's field placement confirmed.

**Q: I expect MCP tools to be agents themselves (agent-as-tool). Elicitation would come back from the other agent, and the caller could answer or escalate to the user. What happens at the protocol levels?**
**A:** MCP doesn't know the tool is an agent; elicitation is B's only channel and B's "user" is A's harness. A sits between two identical patterns facing opposite ways: its own model's `function_call` (LLM API) and B's `input_required` (MCP). A either answers from context and retries B, or escalates (UI form outside the model's view, or feed the question back as tool output and let the model ask). Bites: B's transcript is not in `requestState` (serialise, store+handle, or re-run); sealed-state TTL (600 s default) vs human latency; nesting re-wraps questions hop by hop with stacked TTLs; capabilities are the contract; no token streaming through MCP. For long-running agents, the tasks extension or A2A fit better and are converging. Full note: `experiments/02-mcp/notes/agent-as-tool-elicitation.md`.
**Changed:** new step 2.9 (agent as tool) added to Part 2.

**Q: Let's work on 2.1.**
**A:** Built the study aid: `experiments/02-mcp/notes/trace-to-spec.md`, a two-hour reading order through the 2026-07-28 Basic section plus tools, and a table mapping every line of the 1.6 trace to the spec sentence behind it. Four extra probes filled gaps the trace had not covered: no `_meta` → `-32602`/400; elicitation without the declared capability → `-32021` with `data.requiredCapabilities`; unknown tool → the SDK returns `isError: true` where the spec's example shows a protocol error; bad argument type → `isError: true` with the validation message. Self-check with answers at the end.
**Changed:** 2.1 in progress, pointer updated.


**Q: Where is `_meta` communicated? HTTP header? JSON-RPC property?**
**A:** JSON-RPC property in the body: `params._meta` on requests and notifications, `result._meta` on results. Transport-independent (stdio has no headers at all). Two of its values are additionally *mirrored* into HTTP headers for proxies that route without parsing JSON: `MCP-Protocol-Version` (from `_meta.protocolVersion`) and `Mcp-Method` / `Mcp-Name` (from `method` / `params.name`). The body is the source of truth; the server checks the headers agree (step 4a: `-32020`). `progressToken` lives in `_meta` too.
**Changed:** nothing.

**Q: I see progress messages as SSE, but the claim is "it's not SSE". Elicitation and sampling end the stream; progress doesn't.**
**A:** Progress is SSE; trace step 3 shows it. What 2026-07-28 removed is SSE as a *connection-level channel* (the standalone GET stream, `Last-Event-ID` resume), not SSE as a *response body format*. Every surviving stream belongs to one request and ends with that request's result. Progress and log messages are notifications on that stream and never end it; `complete` and `input_required` are both results and always end it. Elicitation ends the response because in this revision it *is* the response, not because of anything about SSE. Progress for resumed work appears on the retry's stream (6b).
**Changed:** nothing; worth a line in the trace-to-spec note's Part 1 if it trips you again.
