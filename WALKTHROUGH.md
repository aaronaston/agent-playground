# Walkthrough

The linear path through the [study guide](STUDY_GUIDE.md). The guide says *what* and *why*; this file says *do this next*. One step is one sitting. Steps change when a probing question changes the plan; those changes are logged in [QUESTIONS.md](QUESTIONS.md).

## You are here

| | |
|---|---|
| **Now** | Step 1.5 – Capture a Messages API stream (one curl; the first real SSE stream from an LLM API) |
| **Next** | Step 1.6 – Capture an MCP Streamable HTTP session (doubles as the start of Part 2) |
| **Last done** | Step 1.3 – HTTP/1.1 vs HTTP/2, with the multiplexing timeline and the L7/L4 load-balancer demo (2026-10-18) |

Legend: `[x]` done · `[~]` in progress · `[ ]` not started

## Completed log

| Date | Step | One-line takeaway |
|---|---|---|
| 2026-10-17 | 1.1 | SSE is a line-oriented text format on an ordinary HTTP response; `curl -N` shows the whole thing. |
| 2026-10-17 | 1.2 | `Last-Event-ID` is a request header the browser adds on reconnect; resume only means something if events exist independently of connections. |
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

### [ ] 1.5 Capture a Messages API stream
**Goal:** see a real production SSE stream and notice that here the `event:` field carries meaning.

Do (needs `ANTHROPIC_API_KEY` in the environment):
```bash
curl -N https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model":"claude-opus-5-5","max_tokens":200,"stream":true,
       "messages":[{"role":"user","content":"Count to five, one number per line."}]}' \
  | tee experiments/captures/messages-stream.txt
```
Look for: `message_start`, `content_block_start`, repeated `content_block_delta`, `content_block_stop`, `message_delta`, `message_stop`. Note that `event:` names the type *and* the JSON repeats it in a `type` field.

Record: annotate the capture in a comment block at the top of the file: what each event is for and which ones carry usage numbers.

Done when: you can explain every event in the capture.

### [ ] 1.6 Capture an MCP Streamable HTTP session
**Goal:** the bridge into Part 2. See MCP's use of SSE next to the Messages API's and notice the `event:` field is always `message`.

Do: build the smallest possible MCP server with the Python SDK (`uv add mcp`), one tool that sleeps and reports progress, served over Streamable HTTP. Drive it with curl: `tools/list`, then `tools/call`. Save both the requests and responses, headers included, to `experiments/captures/mcp-session.txt`.

Look for: which protocol version the SDK speaks by default (handshake family with `initialize` + `Mcp-Session-Id`, or 2026-07-28 with `_meta` and `Mcp-Method`). The `Accept` header listing both `application/json` and `text/event-stream`. Whether `tools/list` came back as JSON or as a stream.

Done when: you can name every message in the capture and say which revision it is.

### B1 checkpoint
Write the "why SSE, not WebSockets, at all three layers" paragraph in notes.md. Then move the **You are here** block to 2.1.

---

## Part 2 – MCP protocol and features (Track B2)

Working directory: `experiments/02-mcp/` (create it). Spec: https://modelcontextprotocol.io/specification/2026-07-28.

### [ ] 2.1 Versions and the two families
Read the changelogs for 2025-03-26, 2025-06-18, 2025-11-25, 2026-07-28, in order. For each, write one line: what it added, what it removed. Check `mcp_types.version` in the Python SDK for the supported list and the default.

Done when: you can explain the handshake/modern split without notes.

### [ ] 2.2 Minimal server, both transports
Take the server from 1.6. Run it over stdio (drive it with a few hand-typed JSON lines) and over Streamable HTTP. If the SDK lets you pin the protocol version, capture a session in each family.

Done when: two annotated captures exist, one per family.

### [ ] 2.3 Tools, resources, prompts, completion
Add one of each. Return `structuredContent` from the tool. Call all four from an SDK client, then wire the server into Claude Code and see how each primitive surfaces in the UI.

Done when: you can say what a prompt is *for* that a tool isn't.

### [ ] 2.4 Progress and log messages
Make the tool take five seconds and emit `notifications/progress` and `notifications/message` along the way. Watch them arrive on the response stream before the result.

Done when: the capture shows notifications preceding the result on the same stream.

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
