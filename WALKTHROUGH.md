# Walkthrough

The linear path through the [study guide](STUDY_GUIDE.md). The guide says *what* and *why*; this file says *do this next*. One step is one sitting. Steps change when a probing question changes the plan; those changes are logged in [QUESTIONS.md](QUESTIONS.md).

## You are here

| | |
|---|---|
| **Now** | Step 2.1 – MCP versions and the two families (read the four changelogs; you have already seen both families on the wire) |
| **Next** | Step 2.2 – finish the transport pair: stdio by hand, and an SDK client capture |
| **Last done** | Step 1.6 and the B1 checkpoint – MCP server built, both protocol families captured; Part 1 complete (2026-10-18) |

Legend: `[x]` done · `[~]` in progress · `[ ]` not started

## Completed log

| Date | Step | One-line takeaway |
|---|---|---|
| 2026-10-17 | 1.1 | SSE is a line-oriented text format on an ordinary HTTP response; `curl -N` shows the whole thing. |
| 2026-10-17 | 1.2 | `Last-Event-ID` is a request header the browser adds on reconnect; resume only means something if events exist independently of connections. |
| 2026-10-18 | 1.6 | One SDK server answers both MCP families; SSE appears only when there is something to say before the result; header mirroring and session ids are both enforced with a 400. |
| 2026-10-18 | 1.5 | A production LLM stream is plain SSE over one HTTP/2 stream behind a CDN; `event:` carries the type, ordering lives in a `sequence_number`, there is no `Last-Event-ID` resume, and usage arrives only in the final event. |
| 2026-10-18 | 1.3 | ALPN picks the version before any request; HTTP/2 multiplexes streams on one connection so the six-per-host cap and head-of-line blocking disappear; an L7 proxy routes per request, so one client connection never implies one backend. |

---

## Part 1 – Transport foundations (Track B1)

Working directory: `experiments/00-protocols/`. Notes go in `notes.md` there.

### [x] 1.1 Read a raw SSE stream
Done. See `experiments/sse_server.py` and `curl -N http://127.0.0.1:8000/events`.

### [x] 1.2 Tiny SSE server with resume
Done. Server honours `Last-Event-ID`, returns 204 after the final event. Known limitation, recorded in QUESTIONS.md: the stream is a fixed script, so resume is degenerate.

### [x] 1.3 HTTP/1.1 vs HTTP/2
**Goal:** see the differences that matter, which only appear when several requests share a connection: connection count, the browser's per-host cap, and head-of-line blocking. A single request can only show the negotiated version.

Do:
```bash
python experiments/compare_http.py          # one request each: only shows ALPN picked the version
python experiments/multiplex_demo.py --json experiments/captures/multiplex_run.json   # A, B, C; ~15 s
python experiments/multiplex_viz.py         # renders captures/multiplex_run.html; open it in a browser
```
The HTML page draws every transfer as a bar on a shared time axis, grouped into lanes by TCP connection and split into connect / TLS / wait / body phases. Hover a bar for its numbers. The text output below is the same data without the picture.
Look for, in the demo output:
- **A.** Four parallel GETs. HTTP/1.1: `TCP connections: 4`. HTTP/2: `TCP connections: 1` and `stream ids: 1, 3, 5, 7`. Same work, one socket.
- **B.** Eight 2-second requests with HTTP/1.1 capped at six connections (what a browser allows per host): six finish at about 2 s, two more at about 4 s. HTTP/2: all eight finish at about 2 s on one connection with eight streams. In the timeline, find the HTTP/1.1 lane that gets a second bar: it has no connect or TLS segment, because the connection was reused. This is the cap that made the Comet era painful and that SSE over HTTP/1.1 still hits.
- **C.** A 3-second request then an instant one on one connection. HTTP/1.1: the instant one finishes at about 3.3 s, because responses on a connection are strictly ordered. HTTP/2: it finishes at about 0.1 s while the slow stream is still open. That is head-of-line blocking, and its absence.

Then confirm where the version gets chosen:
```bash
curl -v --http2 -o /dev/null https://httpbin.org/get 2>&1 | grep -E 'ALPN|^< HTTP'
```
The `ALPN: server accepted h2` line is inside the TLS handshake, before any request is sent. That is why the 502 run still reported `HTTP version: 2`.

Optional, if Docker is running: `./experiments/lb_demo/run.sh`. It puts two backends behind nginx twice, once as an HTTP (L7) proxy and once as a TCP (L4) proxy, and sends four requests down one client connection to each. Look for: through the L7 proxy the requests alternate between backends, on HTTP/2 streams and on an HTTP/1.1 keep-alive connection alike; through the L4 proxy they all hit one backend. This is the fact behind "sticky routing" in the MCP session discussion: one client connection does not mean one backend once an HTTP-aware proxy is in the path.

Record in notes.md: the three numbers from B and C, and one sentence each on what connection reuse, multiplexing, and head-of-line blocking mean, in your own words. Note the caveat: all HTTP/2 streams still share one TCP connection, so packet loss stalls them together (HTTP/3 is the fix for that; out of scope).

Done when: you can say why a page that opens eight SSE streams behaves differently over HTTP/1.1 and HTTP/2, and where in the connection lifecycle the version is decided.

### [ ] 1.4 SSE vs WebSockets side by side (optional)
**Goal:** see the one structural difference: WebSockets upgrade away from HTTP; SSE never leaves it. Read `experiments/00-protocols/websockets-primer.md` first; then `python experiments/ws_handshake.py` against the running echo server shows the handshake and the frame bytes.

Do:
```bash
python experiments/websocket_server.py        # terminal 1, then open http://127.0.0.1:8765/
python experiments/sse_server.py              # terminal 2, then open http://127.0.0.1:8000/
```
In the browser dev tools Network tab, compare the two connections: the WebSocket shows `101 Switching Protocols` and an `Upgrade: websocket` header, then a Messages tab instead of a Response body. The SSE connection is a normal 200 with a body that keeps growing.

Record: a two-column table in notes.md: handshake, direction, framing, browser API, proxy behaviour, HTTP/2 interaction.

Done when: you can argue for SSE over WebSockets for LLM streaming without mentioning "simpler".

### [x] 1.5 Capture an LLM API stream
Done 2026-10-18 with the OpenAI Responses API (`gpt-4.1-mini`), since that is the key on hand. Script: `experiments/capture_messages_stream.sh`; raw capture and annotation in `experiments/captures/openai-responses-stream.*`. Re-run against the Anthropic Messages API whenever a key exists; the shape is the same family (`message_start`, `content_block_delta`, ...).

What it showed: `event:` names the type and the JSON repeats it; no `id:` lines, ordering is a `sequence_number` in the payload; a fixed opening and closing wrap a run of one-token deltas; usage only in the final event; first byte at 2.4 s, the whole stream in 0.16 s after that.

Also captured: a streamed tool call and its follow-up (`experiments/capture_tool_call.py`, annotated in `captures/openai-tool-call-stream.annotated.md`). Exchange 1 ends `completed` with a `function_call` item instead of text; the client runs the tool; exchange 2 resends the conversation plus the result. Keep this next to the MRTR transcript in `experiments/02-mcp/transcripts/` when doing step 2.5: it is the same pattern.

### [x] 1.6 Capture an MCP Streamable HTTP session
Done 2026-10-18. Server: `experiments/02-mcp/server.py` (mcp SDK 2.3.0, one tool that logs and reports progress). Capture script and annotation: `experiments/02-mcp/capture_session.sh`, `captures/streamable-http-session.*`.

What it showed: the released SDK speaks 2026-07-28 by default and still answers 2025 handshake clients from the same server. `tools/list` came back as plain JSON; only the slow tool call got an SSE stream, with `notifications/message` and `notifications/progress` arriving once a second before the result. `event:` is always `message`. Omitting `Mcp-Method` (2026) or `Mcp-Session-Id` (2025) is a 400. `ctx.info()` warns that logging is deprecated.

### [x] B1 checkpoint
Draft paragraph added to `experiments/00-protocols/notes.md` ("Why SSE at all three layers"). Rewrite it in your own words when you disagree with any of it; that is the test.

---

## Part 2 – MCP protocol and features (Track B2)

Working directory: `experiments/02-mcp/` (create it). Spec: https://modelcontextprotocol.io/specification/2026-07-28.

### [ ] 2.1 Versions and the two families
Read the changelogs for 2025-03-26, 2025-06-18, 2025-11-25, 2026-07-28, in order. For each, write one line: what it added, what it removed. Check `mcp_types.version` in the Python SDK for the supported list and the default.

Done when: you can explain the handshake/modern split without notes.

### [~] 2.2 Minimal server, both transports
Streamable HTTP captures for both families exist from 1.6. Remaining: run `server.py stdio` and drive it with hand-typed JSON lines; capture a session from an SDK *client* and compare with the curl one.

Take the server from 1.6. Run it over stdio (drive it with a few hand-typed JSON lines) and over Streamable HTTP. If the SDK lets you pin the protocol version, capture a session in each family.

Done when: two annotated captures exist, one per family.

### [ ] 2.3 Tools, resources, prompts, completion
Add one of each. Return `structuredContent` from the tool. Call all four from an SDK client, then wire the server into Claude Code and see how each primitive surfaces in the UI.

Done when: you can say what a prompt is *for* that a tool isn't.

### [x] 2.4 Progress and log messages
Done as part of 1.6: `slow_count` emits both, and the capture shows them preceding the result on the same stream in both families. Note the SDK's deprecation warning on `ctx.info()`.

### [ ] 2.5 Elicitation and MRTR
Implement a form-mode elicitation. Trace the round trip twice: as a 2025-style server-initiated `elicitation/create`, and as a 2026-07-28 `input_required` result followed by a retry. Compare each capture against the simulated transcript in `experiments/02-mcp/transcripts/elicitation-two-ways.md` and fix whatever the simulation got wrong.

Done when: you can draw both sequence diagrams from memory.

### [ ] 2.6 Sampling and why it is deprecated
Try `sampling/createMessage` against a 2025-era client. Then read the deprecation rationale in the 2026-07-28 changelog.

Done when: you can state the migration path in one sentence.

### [ ] 2.7 Tasks extension
Wrap the slow tool from 2.4 as a task. Poll it with `tasks/get`.

### [ ] 2.8 Decision table
Function tool vs MCP tool vs A2A. Fill the table in STUDY_GUIDE.md B2.7 and revisit the hypothesis at the top of the guide.

### B2 checkpoint
Tick the B2 progress log in STUDY_GUIDE.md. Move **You are here** to 3.1.

---

## Part 3 – Rung 1 chatbots (Track A)
To be expanded when reached. One step per vendor: OpenAI, Anthropic, LangGraph, Microsoft. Each is a streaming multi-turn chatbot against the lowest-level API, no tools.

## Part 4 – Rung 2 agents (Track A)
To be expanded when reached. One step per vendor on the common benchmark task: one function tool, one MCP tool, one handoff.

## Part 5 – A2A (Track B3)
To be expanded when reached.

## Part 6 – Keycloak and MCP authorization (Track C)
To be expanded when reached.

## Part 7 – Enterprise-managed authorization (Track D)
To be expanded when reached.
