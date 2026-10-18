#!/usr/bin/env python3
"""Drive server.py by hand and narrate every byte, with direction and connection.

No HTTP library: this script opens TCP connections itself, writes the request bytes,
and reads the response bytes, so it can say exactly when a connection opens, which
connection each request rides on, and when each byte arrived.

  →  bytes the client (this script) sent
  ←  bytes the server sent, with the time since the request was written

Start the server first:   uv run python server.py
Then:                     uv run python trace_session.py
Output goes to the terminal and to captures/streamable-http-session.txt
"""
import json
import socket
import sys
import time
from pathlib import Path

HOST, PORT, PATH = "127.0.0.1", 8000, "/mcp"
OUT = Path(__file__).parent / "captures" / "streamable-http-session.txt"
LINES = []


def out(s=""):
    print(s)
    LINES.append(s)


def banner(title, note=None):
    out(); out("─" * 90); out(title)
    if note:
        out("  " + note)
    out("─" * 90)


class Conn:
    count = 0

    def __init__(self):
        Conn.count += 1
        self.n = Conn.count
        self.requests = 0
        self.sock = socket.create_connection((HOST, PORT))
        self.buf = b""
        out(f"  [conn #{self.n}] opened new TCP connection to {HOST}:{PORT}")

    def close(self, why=""):
        self.sock.close()
        out(f"  [conn #{self.n}] closed by client after {self.requests} request(s){'; ' + why if why else ''}")

    # --- raw reading helpers -------------------------------------------------
    def read_until(self, marker, timeout):
        self.sock.settimeout(timeout)
        while marker not in self.buf:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise ConnectionError("server closed the connection")
            self.buf += chunk
        i = self.buf.index(marker) + len(marker)
        data, self.buf = self.buf[:i], self.buf[i:]
        return data

    def read_n(self, n, timeout):
        self.sock.settimeout(timeout)
        while len(self.buf) < n:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise ConnectionError("server closed the connection")
            self.buf += chunk
        data, self.buf = self.buf[:n], self.buf[n:]
        return data


def show_json(prefix, raw):
    try:
        obj = json.loads(raw)
    except Exception:
        out(f"{prefix}{raw}")
        return None
    for line in json.dumps(obj, indent=1).splitlines():
        out(f"{prefix}{line}")
    return obj


def describe(obj):
    if not isinstance(obj, dict):
        return ""
    if "method" in obj and "id" in obj:
        return f"JSON-RPC request id={obj['id']} method={obj['method']}"
    if "method" in obj:
        return f"JSON-RPC notification method={obj['method']}"
    if "result" in obj:
        return f"JSON-RPC result for id={obj['id']}"
    if "error" in obj:
        return f"JSON-RPC error for id={obj['id']}: {obj['error'].get('code')} {obj['error'].get('message')}"
    return ""


def request(conn, step, what, method, headers, body=None, read_timeout=20, idle_note=None):
    banner(f"{step}  ·  {what}")
    conn.requests += 1
    out(f"  [conn #{conn.n}] request #{conn.requests} on this connection")
    out()
    body_bytes = body.encode() if body else b""
    lines = [f"{method} {PATH} HTTP/1.1", f"Host: {HOST}:{PORT}"] + headers
    if body_bytes:
        lines.append(f"Content-Length: {len(body_bytes)}")
    head = "\r\n".join(lines) + "\r\n\r\n"
    out("  client → server  (HTTP request)")
    for l in lines:
        out(f"  → {l}")
    out("  →")
    if body:
        obj = json.loads(body)
        out(f"  → body: {describe(obj)}")
        show_json("  → ", body)
    t0 = time.monotonic()
    conn.sock.sendall(head.encode() + body_bytes)

    # response head
    out()
    out("  server → client  (HTTP response)")
    raw_head = conn.read_until(b"\r\n\r\n", read_timeout).decode()
    hdrs = {}
    for i, l in enumerate(raw_head.split("\r\n")):
        if not l:
            continue
        out(f"  ← {'+%.3fs ' % (time.monotonic() - t0) if i == 0 else '        '}{l}")
        if ":" in l and i > 0:
            k, v = l.split(":", 1); hdrs[k.strip().lower()] = v.strip()
    out("  ←")
    ctype = hdrs.get("content-type", "")
    # response body
    try:
        if "content-length" in hdrs:
            n = int(hdrs["content-length"])
            if n:
                raw = conn.read_n(n, read_timeout).decode()
                obj = json.loads(raw) if ctype.startswith("application/json") else None
                out(f"  ← body ({n} bytes, {ctype or 'no content-type'}): {describe(obj)}")
                show_json("  ← ", raw)
            else:
                out("  ← (empty body)")
        elif hdrs.get("transfer-encoding") == "chunked":
            out(f"  ← body: chunked {ctype}; printing each chunk as it arrives")
            events = 0
            while True:
                size_line = conn.read_until(b"\r\n", read_timeout).decode().strip()
                size = int(size_line.split(";")[0], 16)
                if size == 0:
                    conn.read_until(b"\r\n", read_timeout)
                    out(f"  ← +{time.monotonic() - t0:.3f}s  [end of chunked body: server finished the response]")
                    break
                chunk = conn.read_n(size, read_timeout).decode()
                conn.read_until(b"\r\n", read_timeout)
                stamp = f"+{time.monotonic() - t0:.3f}s"
                for l in chunk.split("\n"):
                    if l.startswith("event:"):
                        events += 1
                        out(f"  ← {stamp}  SSE event #{events}: {l}")
                    elif l.startswith("data:"):
                        obj = json.loads(l[5:].strip())
                        out(f"  ←          data: {describe(obj)}")
                        show_json("  ←            ", l[5:].strip())
                    elif l.strip():
                        out(f"  ← {stamp}  {l}")
        else:
            out("  ← (no body length given)")
    except socket.timeout:
        out(f"  ← +{time.monotonic() - t0:.3f}s  [no more data for {read_timeout}s]{'  ' + idle_note if idle_note else ''}")
    return hdrs


META = {"io.modelcontextprotocol/protocolVersion": "2026-07-28",
        "io.modelcontextprotocol/clientInfo": {"name": "trace-study", "version": "0"},
        "io.modelcontextprotocol/clientCapabilities": {},
        "io.modelcontextprotocol/logLevel": "info"}
ACCEPT = ["Content-Type: application/json", "Accept: application/json, text/event-stream"]


def rpc(id_, method, params):
    return json.dumps({"jsonrpc": "2.0", "id": id_, "method": method, "params": params})


def main():
    out(f"MCP Streamable HTTP trace  ·  {time.strftime('%Y-%m-%d %H:%M:%S')}  ·  server {HOST}:{PORT}{PATH}")
    out("Legend: → sent by client (this script)   ← sent by server, stamped with seconds since the request was sent")

    banner("PART A  ·  speaking 2026-07-28: no handshake, version + capabilities in _meta on every request",
           "All of Part A rides on ONE keep-alive HTTP/1.1 connection, to show that requests, not connections, are the unit.")
    a = Conn()
    request(a, "A1", "MCP tools/list  (expect: plain JSON, nothing to stream)",
            "POST", ACCEPT + ["MCP-Protocol-Version: 2026-07-28", "Mcp-Method: tools/list"],
            rpc(1, "tools/list", {"_meta": META}))
    request(a, "A2", "MCP tools/call slow_count(n=2)  (expect: SSE stream with log + progress, then the result)",
            "POST", ACCEPT + ["MCP-Protocol-Version: 2026-07-28", "Mcp-Method: tools/call", "Mcp-Name: slow_count"],
            rpc(2, "tools/call", {"name": "slow_count", "arguments": {"n": 2}, "_meta": {**META, "progressToken": "p1"}}))
    request(a, "A3", "MCP tools/list again, but WITHOUT the Mcp-Method header  (expect: rejected)",
            "POST", ACCEPT + ["MCP-Protocol-Version: 2026-07-28"],
            rpc(3, "tools/list", {"_meta": META}))
    a.close("Part A done")

    banner("PART B  ·  speaking 2025-06-18: initialize first, then a session id header on everything",
           "Part B uses a fresh connection per request, the way most clients behave, to show the session id doing the correlating.")
    b1 = Conn()
    h = request(b1, "B1", "MCP initialize  (expect: capabilities back, and a session id in a response header)",
                "POST", ACCEPT, rpc(1, "initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                                      "clientInfo": {"name": "trace-study", "version": "0"}}))
    sid = h.get("mcp-session-id", "")
    out(f"\n  >>> server minted session id {sid!r}; the client must now send it on every request")
    b1.close()
    b2 = Conn()
    request(b2, "B2", "MCP notifications/initialized  (a notification: expect 202 and no body)",
            "POST", ACCEPT + ["MCP-Protocol-Version: 2025-06-18", f"Mcp-Session-Id: {sid}"],
            json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}))
    b2.close()
    b3 = Conn()
    request(b3, "B3", "MCP tools/call slow_count(n=2) with the session id  (expect: same stream as A2)",
            "POST", ACCEPT + ["MCP-Protocol-Version: 2025-06-18", f"Mcp-Session-Id: {sid}"],
            rpc(2, "tools/call", {"name": "slow_count", "arguments": {"n": 2}, "_meta": {"progressToken": "p1"}}))
    b3.close()
    b4 = Conn()
    request(b4, "B4", "MCP tools/list WITHOUT the session id  (expect: rejected)",
            "POST", ACCEPT + ["MCP-Protocol-Version: 2025-06-18"], rpc(3, "tools/list", {}))
    b4.close()
    b5 = Conn()
    request(b5, "B5", "HTTP GET: the 2025 standalone server→client stream  (expect: opens and stays silent)",
            "GET", ["Accept: text/event-stream", "MCP-Protocol-Version: 2025-06-18", f"Mcp-Session-Id: {sid}"],
            read_timeout=3, idle_note="nothing server-initiated happened, so nothing was sent; a real client would leave this open")
    b5.close("giving up on the idle stream")
    b6 = Conn()
    request(b6, "B6", "HTTP DELETE: end the session",
            "DELETE", ["MCP-Protocol-Version: 2025-06-18", f"Mcp-Session-Id: {sid}"])
    b6.close()

    banner("SUMMARY")
    out(f"  TCP connections opened by the client: {Conn.count}  (Part A: 1 connection, 3 requests; Part B: {Conn.count - 1} connections, 1 request each)")
    out("  Every MCP message the client sent was its own HTTP request. The server never sent anything the client did not ask for.")
    out("  SSE appeared only on the slow tool call, where the server had notifications to deliver before the result.")
    OUT.write_text("\n".join(LINES) + "\n")
    print(f"\nsaved {OUT}")


if __name__ == "__main__":
    try:
        main()
    except ConnectionRefusedError:
        sys.exit(f"nothing listening on {HOST}:{PORT}. Start the server first: uv run python server.py")
