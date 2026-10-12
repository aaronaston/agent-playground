#!/usr/bin/env python3
"""Serve a short Server-Sent Events stream on localhost."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import time

HTML = Path(__file__).with_name("sse_demo.html")
LAST_EVENT_ID = 5
DONE_EVENT_ID = LAST_EVENT_ID + 1


class SSEHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self):
        if self.path == "/":
            page = HTML.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(page)))
            self.end_headers()
            self.wfile.write(page)
            return

        if self.path != "/events":
            self.send_error(404, "Try /events")
            return

        try:
            last_event_id = int(self.headers.get("Last-Event-ID", "0"))
            if not 0 <= last_event_id <= DONE_EVENT_ID:
                raise ValueError
        except ValueError:
            self.send_error(400, "Invalid Last-Event-ID")
            return

        if last_event_id == DONE_EVENT_ID:
            self.send_response(204)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()

        try:
            for event_id in range(last_event_id + 1, LAST_EVENT_ID + 1):
                payload = json.dumps({"count": event_id, "message": "hello"})
                message = f"id: {event_id}\nevent: update\ndata: {payload}\n\n"
                self.wfile.write(message.encode("utf-8"))
                self.wfile.flush()
                time.sleep(1)
            done_event = f"id: {DONE_EVENT_ID}\nevent: done\ndata: {{}}\n\n"
            self.wfile.write(done_event.encode("utf-8"))
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, format, *args):
        print(f"{self.address_string()} - {format % args}")


if __name__ == "__main__":
    address = ("127.0.0.1", 8000)
    print(f"Serving SSE at http://{address[0]}:{address[1]}/events")
    try:
        ThreadingHTTPServer(address, SSEHandler).serve_forever()
    except KeyboardInterrupt:
        print("\nStopping SSE server.")
