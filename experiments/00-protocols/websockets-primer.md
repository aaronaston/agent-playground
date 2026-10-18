# WebSockets primer

Companion to [`notes.md`](notes.md) and walkthrough step 1.4. Everything here can be
seen on the wire with `experiments/websocket_server.py` (start it) and
`experiments/ws_handshake.py` (talks to it by hand and prints every byte).

## What a WebSocket is

A WebSocket is a TCP connection that **starts as an HTTP/1.1 request and then stops
being HTTP**. After a one-time handshake, both ends send small framed messages in either
direction, at any time, for as long as the connection lives. There are no more requests,
responses, headers, or status codes. It is defined in RFC 6455 (2011).

Three sentences to hold on to:

1. The handshake is HTTP; the conversation afterwards is not.
2. A WebSocket carries *messages*, not events: the protocol gives you text or binary blobs
   and nothing else. Any structure (JSON, message types, request ids) is yours to invent.
3. It is symmetric. Either side can send first, and either side can close.

## 1. The handshake

The client sends an ordinary GET with three special headers:

```http
GET /ws HTTP/1.1
Host: 127.0.0.1:8765
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==
Sec-WebSocket-Version: 13
```

The server answers with a status code that exists for exactly this purpose:

```http
HTTP/1.1 101 Switching Protocols
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=
```

`Sec-WebSocket-Accept` is `base64(sha1(key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"))`.
The fixed GUID is in the RFC. It is not security; it proves the server actually speaks
WebSocket rather than being some HTTP server that happened to echo headers back. You can
see the server compute it in `websocket_server.py`, function `upgrade_and_echo`.

After the blank line that ends the 101, the socket belongs to the WebSocket protocol.
Nothing HTTP-shaped will ever travel on it again. This is the single biggest difference
from SSE, which stays an HTTP response for its whole life.

Because the handshake is a GET, everything a GET can carry is available once: the URL,
query string, cookies, and headers. Browsers do not let JavaScript set custom headers on
the handshake, so bearer tokens usually go in the query string, in a cookie, or in the
first message after connecting. `Sec-WebSocket-Protocol` lets the client propose
subprotocol names (`graphql-ws`, `mqtt`) and the server pick one; it is the only
negotiation the protocol offers.

## 2. Frames

Every message is one or more frames. The header is tiny:

```
 byte 0:  FIN(1) RSV(3) OPCODE(4)
 byte 1:  MASK(1) LEN(7)           LEN 0..125 = length; 126 = next 2 bytes; 127 = next 8 bytes
 [extended length]
 [4-byte masking key, if MASK=1]
 payload
```

A real client frame carrying the text `Hello`, captured from the demo:

```
81 85 37 fa 21 3d 7f 9f 4d 51 58
│  │  └─ masking key ┘ └── "Hello" XOR key ──┘
│  └─ MASK=1, length 5
└─ FIN=1, opcode 1 (text)
```

And the server's echo:

```
81 05 48 65 6c 6c 6f        FIN text, MASK=0, length 5, "Hello" in the clear
```

Opcodes you will meet: `1` text (must be UTF-8), `2` binary, `0` continuation (a message
split across frames; FIN=0 until the last), `8` close, `9` ping, `A` pong. Opcodes 8–10
are **control frames**: they may appear between the fragments of a data message, they are
never fragmented, and their payload is at most 125 bytes.

### Why client frames are masked

Every client→server frame is XORed with a fresh random 4-byte key; server→client frames
never are. The server in the repo enforces this and closes with 1002 if a client frame
arrives unmasked. The reason has nothing to do with secrecy (the key is sent in the clear
right before the payload). It is a defence against **cache poisoning through broken
proxies**: without masking, an attacker's JavaScript could send WebSocket bytes that look
like a plausible HTTP request, and an old transparent proxy that did not understand the
upgrade might parse them as one and cache the "response". Masking makes the byte stream
unpredictable so no intermediary can be tricked into seeing HTTP in it.

## 3. Lifecycle

- **Ping / pong.** Either side may send a ping; the other must answer with a pong carrying
  the same payload. This is the keepalive and liveness check. Browsers answer pings
  automatically but give JavaScript no way to send one, so application-level heartbeats
  (a `{"type":"ping"}` message) are common anyway.
- **Close.** A close frame carries an optional 2-byte status code and reason. The peer
  replies with a close frame, then the TCP connection is torn down. `1000` is normal,
  `1001` going away, `1002` protocol error, `1009` message too big, `1011` server error.
  The demo closes with `03 e8` = 1000.
- **No reconnect, no resume, no replay.** Unlike `EventSource`, the browser `WebSocket`
  object does nothing when the connection drops except fire `close`. Reconnection,
  backoff, re-authentication, and figuring out what was missed are all application code.
  This is the practical reason SSE wins for one-way feeds: you get those for free.

## 4. WebSockets and HTTP/2, HTTP/3, proxies

- The upgrade mechanism above is **HTTP/1.1 only**. HTTP/2 has no `Upgrade` header.
  RFC 8441 (2018) defines WebSockets over an HTTP/2 stream using the extended `CONNECT`
  method with `:protocol = websocket`; RFC 9220 does the same for HTTP/3. Support exists
  in major browsers and some servers, but a great deal of real-world WebSocket traffic
  still runs on a dedicated HTTP/1.1 connection, so each WebSocket costs a whole TCP
  connection in exactly the way demo B of the multiplexing exercise showed.
- An L7 proxy must be told to allow the upgrade (nginx: `proxy_http_version 1.1` plus
  forwarding `Upgrade` and `Connection`). Once upgraded, the proxy becomes a dumb byte
  pipe for that connection: it can no longer route per message, because there are no
  requests to route. The connection is pinned to one backend for its life, which is the
  opposite of what you saw in `lb_demo` for ordinary HTTP.
- Idle-timeout killers (load balancers, NAT) will drop a quiet WebSocket. Hence pings.

## 5. WebSockets vs SSE, in one table

| | SSE | WebSocket |
|---|---|---|
| Starts as | HTTP response that never ends | HTTP GET that becomes something else |
| Stays HTTP | yes | no, after the 101 |
| Direction | server → client | both, symmetric |
| Payload | UTF-8 text, line-oriented event format | text or binary frames, no format |
| Browser reconnect | automatic, with `Last-Event-ID` | none |
| Custom headers from browser JS | no (`EventSource`), yes with `fetch` | no |
| Over HTTP/2 | just another stream | needs RFC 8441; often a separate h1.1 connection |
| Through an L7 proxy | routed per request like any response | pinned to one backend after upgrade |
| Good for | feeds, token streams, progress | chat, games, collaborative editing, anything chatty both ways |

## 6. Why LLM APIs and MCP did not pick it

An LLM request is one client message followed by a long server answer. That is a
response, so SSE fits without inventing a message protocol, keeps auth in normal
headers, works through every proxy and CDN, multiplexes over HTTP/2 for free, and
reconnects by itself. MCP needs more than one direction, but it needs it per *request*,
not per *connection*, and it wanted stateless servers behind ordinary load balancers.
Streamable HTTP gets that by making every client message its own request. A WebSocket
would have forced every MCP server to be a long-lived stateful process pinned to one
backend, which is exactly what the 2026-07-28 revision was trying to eliminate.

## References

- RFC 6455, The WebSocket Protocol: https://www.rfc-editor.org/rfc/rfc6455
- RFC 8441, Bootstrapping WebSockets with HTTP/2: https://www.rfc-editor.org/rfc/rfc8441
- RFC 9220, Bootstrapping WebSockets with HTTP/3: https://www.rfc-editor.org/rfc/rfc9220
- MDN, Writing WebSocket servers: https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API/Writing_WebSocket_servers
