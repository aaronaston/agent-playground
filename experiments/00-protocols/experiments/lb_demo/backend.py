"""Minimal HTTP/1.1 backend that says which host served the request."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import socket

class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def do_GET(self):
        body = f"served by {socket.gethostname()}\n".encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, *a): pass

ThreadingHTTPServer(("0.0.0.0", 8000), H).serve_forever()
