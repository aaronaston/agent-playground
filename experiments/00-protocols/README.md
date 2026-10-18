# Protocol Warm-up

This folder is the hands-on start of **Track B1** in [`STUDY_GUIDE.md`](../../STUDY_GUIDE.md). Read [`notes.md`](notes.md), then run the examples in `experiments/`. They use Python's standard library; the HTTP comparison also needs `curl`.

## Layout

- `notes.md` — protocol concepts, tradeoffs, and references.
- `websockets-primer.md` — what a WebSocket is, byte by byte, and how it compares with SSE.
- `experiments/sse_server.py`, `sse_client.py`, and `sse_demo.html` — a small SSE stream, Python reader, and browser client using the native `EventSource` API.
- `experiments/websocket_server.py` and `websocket_demo.html` — a local WebSocket echo server and browser client.
- `experiments/ws_handshake.py` — talks to the echo server by hand and prints the handshake, a masked frame, the echo, and the close.
- `experiments/compare_http.py` — one request each over HTTP/1.1 and HTTP/2: shows which version ALPN negotiated.
- `experiments/multiplex_demo.py` — several requests at once: connection count, the browser's six-per-host cap, and head-of-line blocking.
- `experiments/multiplex_viz.py` — renders a `--json` capture from `multiplex_demo.py` as an HTML timeline (lanes per TCP connection, bars split into connect / TLS / wait / body).
- `experiments/lb_demo/` — two backends behind nginx as an L7 (HTTP) proxy and as an L4 (TCP) proxy; shows that an L7 proxy routes each request on one client connection independently. Needs Docker.

## Run the experiments

### SSE

In one terminal:

```bash
cd experiments/00-protocols
python experiments/sse_server.py
```

Open <http://127.0.0.1:8000/> in a browser to watch events arrive through the browser's built-in `EventSource` client. The server sends a `done` event after the updates; if the connection is interrupted earlier, `EventSource` reconnects using the last event ID.

You can also read the stream with the Python client:

```bash
cd experiments/00-protocols
python experiments/sse_client.py
```

Or inspect the raw wire format:

```bash
curl -N http://127.0.0.1:8000/events
```

The server sends a finite sequence of events and closes the response. `-N` disables curl's output buffering so each event is visible as it arrives.

### WebSockets

Start the local server:

```bash
cd experiments/00-protocols
python experiments/websocket_server.py
```

Open <http://127.0.0.1:8765/> in a browser, connect, and send a message. The browser and server can both initiate messages; the server echoes text messages. The intentionally small server supports local text and control frames for learning only; it is not a production WebSocket implementation.

### HTTP/1.1 vs. HTTP/2

```bash
cd experiments/00-protocols
python experiments/compare_http.py
python experiments/multiplex_demo.py --json experiments/captures/multiplex_run.json   # or: ... B --json ...
python experiments/multiplex_viz.py       # writes experiments/captures/multiplex_run.html
```

`compare_http.py` makes one HTTP/1.1 and one HTTP/2 request and prints the negotiated version and timings. On its own that only shows that ALPN picked the version during the TLS handshake. `multiplex_demo.py` runs several transfers at once with `curl -Z` and prints a timeline: four parallel GETs (four connections vs. one connection with four streams), eight slow requests under a browser-style six-connection cap (two waves vs. one), and a fast request queued behind a slow one on a single connection (head-of-line blocking vs. none). Both scripts use httpbin.org; pass another HTTPS URL to `compare_http.py` if desired. Network conditions affect the numbers but not the shape.

### Load balancers and connection reuse

```bash
cd experiments/00-protocols
./experiments/lb_demo/run.sh      # needs Docker; pulls python:3.12-alpine and nginx:alpine
```

Starts `backend1` and `backend2` and an nginx with two listeners: `:8080` is an HTTP (L7) proxy that speaks HTTP/2 to the client and HTTP/1.1 to the backends; `:8081` is a TCP (L4) proxy. Four requests on one client connection go to both backends through `:8080` (over HTTP/2 streams and over HTTP/1.1 keep-alive alike) and to a single backend through `:8081`. Containers are removed on exit.

## Continue the study

After these warm-ups, follow B1's checklist in `STUDY_GUIDE.md`: capture a real LLM stream, then examine MCP Streamable HTTP. Treat protocol choice as a fit to message direction, deployment constraints, and failure behavior—not as a ranking. Add later exercises under `experiments/` and keep notes/references in `notes.md`.
