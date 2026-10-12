#!/usr/bin/env python3
"""A small localhost WebSocket text echo server for the browser demo."""

import base64
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
MAX_MESSAGE_SIZE = 1024 * 1024
HTML = Path(__file__).with_name("websocket_demo.html")


def read_exact(stream, length):
    data = stream.read(length)
    if len(data) != length:
        raise ConnectionError("Client disconnected mid-frame")
    return data


def read_frame(stream):
    first, second = read_exact(stream, 2)
    final = first & 0x80
    opcode = first & 0x0F
    masked = second & 0x80
    length = second & 0x7F
    if length == 126:
        length = int.from_bytes(read_exact(stream, 2), "big")
    elif length == 127:
        length = int.from_bytes(read_exact(stream, 8), "big")
    if length > MAX_MESSAGE_SIZE:
        raise ValueError("Frame exceeds the 1 MiB demo limit")
    if not masked:
        raise ValueError("Browser-to-server frames must be masked")
    mask = read_exact(stream, 4)
    payload = read_exact(stream, length)
    payload = bytes(value ^ mask[index % 4] for index, value in enumerate(payload))
    return final, opcode, payload


def write_frame(stream, opcode, payload=b""):
    length = len(payload)
    header = bytes((0x80 | opcode,))
    if length < 126:
        header += bytes((length,))
    elif length <= 65535:
        header += bytes((126,)) + length.to_bytes(2, "big")
    else:
        header += bytes((127,)) + length.to_bytes(8, "big")
    stream.write(header + payload)
    stream.flush()


class WebSocketHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self):
        if self.path == "/":
            page = HTML.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(page)))
            self.end_headers()
            self.wfile.write(page)
        elif self.path == "/ws":
            self.upgrade_and_echo()
        else:
            self.send_error(404)

    def upgrade_and_echo(self):
        key = self.headers.get("Sec-WebSocket-Key")
        if self.headers.get("Upgrade", "").lower() != "websocket" or not key:
            self.send_error(400, "Expected a WebSocket upgrade")
            return

        accept = base64.b64encode(
            hashlib.sha1((key + GUID).encode("ascii")).digest()
        ).decode("ascii")
        self.send_response(101, "Switching Protocols")
        self.send_header("Upgrade", "websocket")
        self.send_header("Connection", "Upgrade")
        self.send_header("Sec-WebSocket-Accept", accept)
        self.end_headers()
        self.wfile.flush()

        try:
            while True:
                final, opcode, payload = read_frame(self.rfile)
                if not final:
                    write_frame(self.wfile, 8, b"\x03\xF0")
                    break
                if opcode == 8:
                    write_frame(self.wfile, 8, payload[:125])
                    break
                if opcode == 9:
                    write_frame(self.wfile, 10, payload)
                elif opcode == 1:
                    write_frame(self.wfile, 1, payload)
                else:
                    write_frame(self.wfile, 8, b"\x03\xEA")
                    break
        except (ConnectionError, OSError, ValueError):
            pass
        finally:
            self.close_connection = True

    def log_message(self, format, *args):
        print(f"{self.address_string()} - {format % args}")


if __name__ == "__main__":
    address = ("127.0.0.1", 8765)
    print(f"Open http://{address[0]}:{address[1]}/ for the WebSocket demo")
    try:
        ThreadingHTTPServer(address, WebSocketHandler).serve_forever()
    except KeyboardInterrupt:
        print("\nStopping WebSocket server.")
