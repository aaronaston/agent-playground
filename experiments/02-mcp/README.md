# 02 – MCP: the protocol and its features

Hands-on for **Track B2** of the [study guide](../../STUDY_GUIDE.md), Part 2 of the
[walkthrough](../../WALKTHROUGH.md). Python SDK `mcp` 2.x (`MCPServer`, formerly FastMCP).

## Setup

```bash
cd experiments/02-mcp
uv sync
```

## What is here

- `server.py` – the smallest useful server: `slow_count(n)`, which logs and reports progress once a second; `weather()`, which asks the user which city via elicitation (a `Resolve`/`Elicit` resolver, so under 2026-07-28 it becomes an `input_required` round trip); and `announce_change()`, which pushes a `tools/list_changed` notification to anyone listening. `PORT=8001` changes the port. `uv run python server.py` serves Streamable HTTP on `http://127.0.0.1:8000/mcp`; add `stdio` to speak stdio instead.
- `trace_session.py` – drives the running server by hand over raw TCP sockets as a **2026-07-28** client (`--legacy` appends the 2025 handshake family for comparison) and narrates every byte: `→` lines are what the client sent, `←` lines are what the server sent with the time since the request, and each connection is numbered so you can see which request rode on which socket. Saves to `captures/streamable-http-session.txt`; commentary in `captures/streamable-http-session.annotated.md`.
- `notes/trace-to-spec.md` – step 2.1: reading order for the 2026-07-28 spec and a line-by-line map from the trace to the spec rule behind each message, plus where the SDK differs from the spec's examples.
- `notes/agent-as-tool-elicitation.md` – design note: what happens at each layer when the tool is itself an agent and raises an elicitation; the calling agent answers or escalates.
- `transcripts/elicitation-two-ways.md` – a simulated HTTP/2 transcript of a tool call that needs user input, in the 2025 (server request on the stream) and 2026 (MRTR retry) styles. To be checked against a real capture in step 2.5.

## Run the capture yourself

```bash
uv run python server.py            # terminal 1
uv run python trace_session.py     # terminal 2; ~12 s
```

## Reading the trace

Each step has a banner saying what MCP call is being made and what to expect. Under it, the HTTP request the client wrote (every header, then the JSON-RPC body pretty-printed and labelled "request id=N method=..."), then the HTTP response as it arrived: status line and headers, then either a JSON body or, for a stream, each SSE event with a timestamp and its JSON-RPC payload labelled as a notification or a result. Connection lines (`[conn #N] opened` / `closed`) mark the TCP boundaries. Part 1 deliberately puts three requests on one connection; the rest open a fresh connection per request; step 5 keeps one open on purpose and triggers a notification onto it from another.

## Notes so far (protocol 2026-07-28)

- No handshake, no sessions. `server/discover` is optional. Version, identity and capabilities ride in `_meta` on every request.
- `tools/list` and most results come back as plain JSON. SSE appears only when the server has notifications to send before a result, and on `subscriptions/listen`.
- `Mcp-Method` is enforced (`-32020`); an unknown version gets `-32022` with the supported list; `GET` is `405`.
- `subscriptions/listen` is the only server→client channel: opt in, get an acknowledgement, notifications arrive tagged with the subscription id, close the stream to unsubscribe.
- When a tool needs the user, the call returns `resultType: input_required` with `inputRequests` and a sealed `requestState`; the client retries the same call with `inputResponses` and the state echoed back. Tamper with the state and the retry is refused. `ctx.elicit()` directly raises "no back-channel" on this transport; use `Annotated[T, Resolve(fn)]` with a resolver returning `Elicit(...)`.
- `ctx.info()` works but warns that the logging capability is deprecated (SEP-2577).
- The same server still answers 2025-06-18 clients; see `--legacy`.
