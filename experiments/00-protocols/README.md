# Protocol Warm-up

This folder is the hands-on start of **Track B1** in [`STUDY_GUIDE.md`](../../STUDY_GUIDE.md). Read [`notes.md`](notes.md), then run the examples in `experiments/`. They use Python's standard library; the HTTP comparison also needs `curl`.

## Layout

- `notes.md` — protocol concepts, tradeoffs, and references.
- `experiments/sse_server.py` and `sse_client.py` — a small SSE stream and reader.
- `experiments/websocket_server.py` and `websocket_demo.html` — a local WebSocket echo server and browser client.
- `experiments/compare_http.py` — compare HTTP/1.1 and HTTP/2 negotiation and timing against a TLS endpoint.

## Run the experiments

### SSE

In one terminal:

```bash
cd experiments/00-protocols
python experiments/sse_server.py
```

In another terminal, read the stream with the Python client:

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
```

The script uses `curl` to make separate HTTP/1.1 and HTTP/2 requests to a public HTTPS test endpoint and prints the negotiated HTTP version and timings. HTTP/2 requires a curl build with HTTP/2 support; pass another HTTPS URL as the first argument if desired. Compare output, then try `curl -N -v --http1.1 URL` and `curl -N -v --http2 URL` against a streaming endpoint to inspect response chunks. Network access and the remote endpoint affect results.

## Continue the study

After these warm-ups, follow B1's checklist in `STUDY_GUIDE.md`: capture a real LLM stream, then examine MCP Streamable HTTP. Treat protocol choice as a fit to message direction, deployment constraints, and failure behavior—not as a ranking. Add later exercises under `experiments/` and keep notes/references in `notes.md`.
