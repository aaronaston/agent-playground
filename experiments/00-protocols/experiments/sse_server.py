#!/usr/bin/env python3
"""Serve a short Server-Sent Events stream on localhost."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import time


class SSEHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self):
        if self.path != "/events":
            self.send_error(404, "Try /events")
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()

        try:
            for event_id in range(1, 6):
                payload = json.dumps({"count": event_id, "message": "hello"})
                message = f"id: {event_id}\nevent: update\ndata: {payload}\n\n"
                self.wfile.write(message.encode("utf-8"))
                self.wfile.flush()
                time.sleep(1)
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
