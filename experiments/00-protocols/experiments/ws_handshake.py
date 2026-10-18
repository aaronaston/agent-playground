#!/usr/bin/env python3
"""Talk to websocket_server.py by hand and print every byte.

Shows the four things that make up a WebSocket: the HTTP/1.1 upgrade handshake,
a masked client frame, an unmasked server frame, and the close exchange.
Start the server first: python experiments/websocket_server.py
"""
import base64
import hashlib
import socket

GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
KEY = "dGhlIHNhbXBsZSBub25jZQ=="  # the example key from RFC 6455 section 1.3
MASK = bytes([0x37, 0xFA, 0x21, 0x3D])


def masked(payload):
    return bytes(b ^ MASK[i % 4] for i, b in enumerate(payload))


s = socket.create_connection(("127.0.0.1", 8765))
req = ("GET /ws HTTP/1.1\r\nHost: 127.0.0.1:8765\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
       f"Sec-WebSocket-Key: {KEY}\r\nSec-WebSocket-Version: 13\r\n\r\n")
print("=== 1. handshake request: an ordinary HTTP/1.1 GET ===\n" + req.strip())
s.sendall(req.encode())
print("\n=== 2. handshake response: 101, and HTTP is over on this socket ===\n" + s.recv(4096).decode().strip())
expect = base64.b64encode(hashlib.sha1((KEY + GUID).encode()).digest()).decode()
print(f"\n   Sec-WebSocket-Accept should be base64(sha1(key + GUID)) = {expect}")

frame = bytes([0x81, 0x80 | 5]) + MASK + masked(b"Hello")
print("\n=== 3. client frame: text 'Hello', masked (client->server frames must be) ===")
print("bytes:", frame.hex(" "))
print("  81           FIN=1, opcode=1 (text)")
print("  85           MASK=1, payload length=5")
print("  37 fa 21 3d  masking key")
print("  7f 9f 4d 51 58  'Hello' XOR key, byte by byte")
s.sendall(frame)
echo = s.recv(4096)
print("\n=== 4. server frame: the echo, unmasked ===")
print("bytes:", echo.hex(" "), "   81 05 = FIN text, MASK=0, length 5; payload in the clear:", echo[2:].decode())

s.sendall(bytes([0x88, 0x80 | 2]) + MASK + masked(b"\x03\xe8"))
close = s.recv(4096)
print("\n=== 5. close: opcode 8 with a 2-byte status; 1000 = normal ===")
print("client: 88 82 <mask> <03e8 masked>")
print("server:", close.hex(" "))
s.close()
