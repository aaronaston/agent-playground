#!/usr/bin/env python3
"""Drive server.py by hand, speaking MCP 2026-07-28, and narrate every byte.

No HTTP library: this script opens TCP connections itself, writes the request bytes,
and reads the response bytes, so it can say exactly when a connection opens, which
connection each request rides on, and when each byte arrived.

  →  bytes the client (this script) sent
  ←  bytes the server sent, with the time since the request was written

Start the server first:   uv run python server.py
Then:                     uv run python trace_session.py            # current protocol only
                          uv run python trace_session.py --legacy   # plus the 2025 handshake family
Output goes to the terminal and to captures/streamable-http-session.txt
"""
import json
import os
import socket
import sys
import time
from pathlib import Path

HOST, PORT, PATH = "127.0.0.1", int(os.environ.get("PORT", "8000")), "/mcp"
OUT = Path(__file__).parent / "captures" / "streamable-http-session.txt"
LINES = []
LAST = []   # JSON objects parsed from the most recent response


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
    if prefix.strip().startswith("←"):
        LAST.append(obj)
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
    LAST.clear()
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
        "io.modelcontextprotocol/clientCapabilities": {"elicitation": {"form": {}}},
        "io.modelcontextprotocol/logLevel": "info"}
ACCEPT = ["Content-Type: application/json", "Accept: application/json, text/event-stream"]


def rpc(id_, method, params):
    return json.dumps({"jsonrpc": "2.0", "id": id_, "method": method, "params": params})


def listen_then_trigger():
    """subscriptions/listen on one connection, then make something happen on another."""
    banner("5  ·  subscriptions/listen: the modern server→client channel",
           "A POST whose response stream stays open. We open it on conn #L, then on another connection call a tool that "
           "changes the tool set, and watch the notification arrive on conn #L.")
    L = Conn()
    body = rpc(5, "subscriptions/listen", {"notifications": {"toolsListChanged": True}, "_meta": META})
    L.requests += 1
    out(f"  [conn #{L.n}] request #1 on this connection")
    out(); out("  client → server  (HTTP request)")
    lines = [f"POST {PATH} HTTP/1.1", f"Host: {HOST}:{PORT}"] + ACCEPT + ["MCP-Protocol-Version: 2026-07-28",
             "Mcp-Method: subscriptions/listen", f"Content-Length: {len(body)}"]
    for l in lines:
        out(f"  → {l}")
    out("  →"); out(f"  → body: {describe(json.loads(body))}"); show_json("  → ", body)
    t0 = time.monotonic()
    L.sock.sendall(("\r\n".join(lines) + "\r\n\r\n").encode() + body.encode())
    out(); out("  server → client  (HTTP response; this stream will stay open)")
    head = L.read_until(b"\r\n\r\n", 10).decode()
    for i, l in enumerate(head.split("\r\n")):
        if l:
            out(f"  ← {'+%.3fs ' % (time.monotonic() - t0) if i == 0 else '        '}{l}")
    out("  ←")

    def read_events(conn, timeout, label):
        try:
            while True:
                size = int(conn.read_until(b"\r\n", timeout).decode().split(";")[0], 16)
                if size == 0:
                    out(f"  ← [conn #{conn.n}] stream ended by server"); return
                chunk = conn.read_n(size, timeout).decode(); conn.read_until(b"\r\n", timeout)
                stamp = f"+{time.monotonic() - t0:.3f}s"
                for l in chunk.split("\n"):
                    if l.startswith("event:"):
                        out(f"  ← {stamp}  [conn #{conn.n}] SSE {l}")
                    elif l.startswith("data:"):
                        out(f"  ←          data: {describe(json.loads(l[5:]))}"); show_json("  ←            ", l[5:].strip())
        except socket.timeout:
            out(f"  ← +{time.monotonic() - t0:.3f}s  [conn #{conn.n}] {label}")

    read_events(L, 2, "quiet: the acknowledgement came, nothing else has happened yet")
    out(); out(f"  >>> leaving conn #{L.n} open; now trigger a change from a second connection")
    T = Conn()
    request(T, "5b", "MCP tools/call announce_change  (the server will push tools/list_changed to listeners)",
            "POST", ACCEPT + ["MCP-Protocol-Version: 2026-07-28", "Mcp-Method: tools/call", "Mcp-Name: announce_change"],
            rpc(6, "tools/call", {"name": "announce_change", "arguments": {}, "_meta": META}))
    T.close()
    out(); out(f"  >>> back to conn #{L.n}: did anything arrive on the listen stream?")
    read_events(L, 2, "quiet again")
    L.close("done listening; closing the stream is how a client unsubscribes")


def weather_round_trip():
    banner("6  ·  a tool that needs the user: MRTR (multi round-trip request)",
           "Call weather with no arguments. The server cannot ask the client anything directly in this protocol, so it ends "
           "the response with resultType input_required, packs its position into requestState, and stops. The client "
           "collects the answer and retries the same call with inputResponses and the state echoed back.")
    c = Conn()
    request(c, "6a", "MCP tools/call weather, no arguments  (expect: input_required with an elicitation/create inside)",
            "POST", ACCEPT + ["MCP-Protocol-Version: 2026-07-28", "Mcp-Method: tools/call", "Mcp-Name: weather"],
            rpc(7, "tools/call", {"name": "weather", "arguments": {}, "_meta": META}))
    c.close()
    res = next((o["result"] for o in LAST if "result" in o), {})
    reqs = res.get("inputRequests", {})
    state = res.get("requestState")
    if res.get("resultType") != "input_required" or not reqs:
        out("  !! expected input_required; got something else, stopping this step"); return
    key, ask = next(iter(reqs.items()))
    out(); out(f"  >>> the response is finished (HTTP-wise) but the tool is not: resultType={res['resultType']!r}")
    out(f"  >>> the server asked one question, keyed {key!r}: {ask['method']} \"{ask['params'].get('message')}\"")
    out(f"  >>> requestState is {len(state or '')} chars of sealed, opaque server state; the client must echo it unchanged")
    out("  >>> (the user is now shown the question and types: Toronto)")
    answer = {key: {"action": "accept", "content": {"city": "Toronto"}}}
    c = Conn()
    request(c, "6b", "MCP tools/call weather AGAIN, same arguments + inputResponses + requestState  (expect: log, then the real result)",
            "POST", ACCEPT + ["MCP-Protocol-Version: 2026-07-28", "Mcp-Method: tools/call", "Mcp-Name: weather"],
            rpc(8, "tools/call", {"name": "weather", "arguments": {}, "inputResponses": answer, "requestState": state, "_meta": META}))
    c.close()
    c = Conn()
    request(c, "6c", "the same retry with ONE character changed in requestState  (expect: rejected; the seal is checked)",
            "POST", ACCEPT + ["MCP-Protocol-Version: 2026-07-28", "Mcp-Method: tools/call", "Mcp-Name: weather"],
            rpc(9, "tools/call", {"name": "weather", "arguments": {}, "inputResponses": answer, "requestState": (state or "") + "x", "_meta": META}))
    c.close()
    c = Conn()
    request(c, "6d", "the retry where the user DECLINED to answer  (expect: the call ends without weather)",
            "POST", ACCEPT + ["MCP-Protocol-Version: 2026-07-28", "Mcp-Method: tools/call", "Mcp-Name: weather"],
            rpc(10, "tools/call", {"name": "weather", "arguments": {}, "inputResponses": {key: {"action": "decline"}}, "requestState": state, "_meta": META}))
    c.close()


def legacy():
    banner("APPENDIX  ·  the 2025-06-18 handshake family, for comparison only",
           "initialize first, then a session id header on everything. Fresh connection per request.")
    b1 = Conn()
    h = request(b1, "L1", "MCP initialize  (expect: capabilities back, and a session id in a response header)",
                "POST", ACCEPT, rpc(1, "initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                                      "clientInfo": {"name": "trace-study", "version": "0"}}))
    sid = h.get("mcp-session-id", "")
    out(f"\n  >>> server minted session id {sid!r}; the client must now send it on every request")
    b1.close()
    b2 = Conn()
    request(b2, "L2", "MCP notifications/initialized  (a notification: expect 202 and no body)",
            "POST", ACCEPT + ["MCP-Protocol-Version: 2025-06-18", f"Mcp-Session-Id: {sid}"],
            json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}))
    b2.close()
    b3 = Conn()
    request(b3, "L3", "MCP tools/call slow_count(n=2) with the session id",
            "POST", ACCEPT + ["MCP-Protocol-Version: 2025-06-18", f"Mcp-Session-Id: {sid}"],
            rpc(2, "tools/call", {"name": "slow_count", "arguments": {"n": 2}, "_meta": {"progressToken": "p1"}}))
    b3.close()
    b4 = Conn()
    request(b4, "L4", "MCP tools/list WITHOUT the session id  (expect: rejected)",
            "POST", ACCEPT + ["MCP-Protocol-Version: 2025-06-18"], rpc(3, "tools/list", {}))
    b4.close()
    b5 = Conn()
    request(b5, "L5", "HTTP GET: the 2025 standalone server→client stream  (expect: opens and stays silent)",
            "GET", ["Accept: text/event-stream", "MCP-Protocol-Version: 2025-06-18", f"Mcp-Session-Id: {sid}"],
            read_timeout=3, idle_note="nothing server-initiated happened; a real client would leave this open")
    b5.close("giving up on the idle stream")
    b6 = Conn()
    request(b6, "L6", "HTTP DELETE: end the session", "DELETE", ["MCP-Protocol-Version: 2025-06-18", f"Mcp-Session-Id: {sid}"])
    b6.close()


def main():
    want_legacy = "--legacy" in sys.argv
    out(f"MCP Streamable HTTP trace  ·  protocol 2026-07-28  ·  {time.strftime('%Y-%m-%d %H:%M:%S')}  ·  server {HOST}:{PORT}{PATH}")
    out("Legend: → sent by client (this script)   ← sent by server, stamped with seconds since the request was sent")
    out("There is no handshake in this protocol version. Every request carries the protocol version, client identity and")
    out("capabilities in params._meta, and mirrors its method into the Mcp-Method header for proxies.")

    banner("PART 1  ·  discovery and the tool list, three requests on ONE keep-alive connection",
           "To show that the unit of the protocol is the request, not the connection.")
    a = Conn()
    request(a, "1", "MCP server/discover  (optional first call: which versions and capabilities does this server have?)",
            "POST", ACCEPT + ["MCP-Protocol-Version: 2026-07-28", "Mcp-Method: server/discover"],
            rpc(1, "server/discover", {"_meta": META}))
    request(a, "2", "MCP tools/list  (expect: plain JSON, nothing to stream)",
            "POST", ACCEPT + ["MCP-Protocol-Version: 2026-07-28", "Mcp-Method: tools/list"],
            rpc(2, "tools/list", {"_meta": META}))
    request(a, "3", "MCP tools/call slow_count(n=2)  (expect: SSE stream with log + progress, then the result)",
            "POST", ACCEPT + ["MCP-Protocol-Version: 2026-07-28", "Mcp-Method: tools/call", "Mcp-Name: slow_count"],
            rpc(3, "tools/call", {"name": "slow_count", "arguments": {"n": 2}, "_meta": {**META, "progressToken": "p1"}}))
    a.close("Part 1 done")

    banner("PART 2  ·  what the server rejects, one fresh connection each")
    c = Conn()
    request(c, "4a", "tools/list WITHOUT the Mcp-Method header  (expect: 400, HeaderMismatch)",
            "POST", ACCEPT + ["MCP-Protocol-Version: 2026-07-28"], rpc(4, "tools/list", {"_meta": META}))
    c.close()
    c = Conn()
    bad = {**META, "io.modelcontextprotocol/protocolVersion": "2027-01-01"}
    request(c, "4b", "tools/list claiming protocol version 2027-01-01  (expect: 400, UnsupportedProtocolVersion with the supported list)",
            "POST", ACCEPT + ["MCP-Protocol-Version: 2027-01-01", "Mcp-Method: tools/list"], rpc(4, "tools/list", {"_meta": bad}))
    c.close()
    c = Conn()
    request(c, "4c", "HTTP GET on the endpoint  (the 2025 standalone stream; expect: 405, it no longer exists)",
            "GET", ["Accept: text/event-stream", "MCP-Protocol-Version: 2026-07-28"])
    c.close()

    listen_then_trigger()
    weather_round_trip()

    if want_legacy:
        legacy()

    banner("SUMMARY")
    out(f"  TCP connections opened by the client: {Conn.count}")
    out("  Every MCP message the client sent was its own HTTP request. The server never sent anything the client did not ask for,")
    out("  and when it needed the user it ended its response with input_required and waited for a retry (step 6).")
    out("  and the only long-lived stream was the one the client opened on purpose with subscriptions/listen.")
    out("  SSE appeared on the slow tool call (notifications before the result) and on the listen stream; everything else was plain JSON.")
    if not want_legacy:
        out("  Run with --legacy to append the 2025-06-18 handshake-and-session family for comparison.")
    OUT.write_text("\n".join(LINES) + "\n")
    print(f"\nsaved {OUT}")


if __name__ == "__main__":
    try:
        main()
    except ConnectionRefusedError:
        sys.exit(f"nothing listening on {HOST}:{PORT}. Start the server first: uv run python server.py")
