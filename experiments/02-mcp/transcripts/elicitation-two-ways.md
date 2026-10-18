# Simulated transcript: a tool call that needs user input, two ways

**Simulated, not captured.** Field names and header rules follow the spec text; the
values, the tool, and the timings are invented. Written for walkthrough step 2.5.

Scenario: the client calls `deploy_service` for `billing@2.14.0`. Partway through, the
server needs the user to choose an environment. Everything runs over one HTTP/2
connection. Client-initiated streams are odd-numbered (1, 3, 5...), each HTTP request is
its own stream, and `→` is client to server, `←` is server to client.

---

## A. 2026-07-28: Multi Round-Trip Requests (the current spec)

The server cannot send requests to the client. When it needs input it returns a
*result* of type `input_required`, the stream closes, and the client retries the whole
call with the answers attached. Two independent HTTP exchanges.

### Stream 1 → `tools/call` (attempt 1)

```http
HEADERS (stream 1)
:method: POST
:path: /mcp
:authority: deployer.example.net
content-type: application/json
accept: application/json, text/event-stream
authorization: Bearer eyJhbGciOi…
mcp-protocol-version: 2026-07-28
mcp-method: tools/call
mcp-name: deploy_service

DATA (stream 1, END_STREAM)
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "deploy_service",
    "arguments": { "service": "billing", "version": "2.14.0" },
    "_meta": {
      "io.modelcontextprotocol/protocolVersion": "2026-07-28",
      "io.modelcontextprotocol/clientInfo": { "name": "study-client", "version": "0.1" },
      "io.modelcontextprotocol/clientCapabilities": { "elicitation": { "form": {} } },
      "io.modelcontextprotocol/logLevel": "info",
      "progressToken": "dep-1"
    }
  }
}
```

Notes: no `initialize` happened before this; version, identity and capabilities ride in
`_meta` on every request. `logLevel` is what entitles the server to send log messages
on this stream. `Mcp-Method` and `Mcp-Name` mirror body fields so a gateway can route
without parsing JSON.

### Stream 1 ← SSE response, ends with `input_required`

```http
HEADERS (stream 1)
:status: 200
content-type: text/event-stream
cache-control: no-cache
x-accel-buffering: no

DATA (stream 1)
event: message
data: {"jsonrpc":"2.0","method":"notifications/message","params":{"level":"info","logger":"deploy","data":"Resolved billing@2.14.0 to image sha256:9f3c1a…"}}

DATA (stream 1)
event: message
data: {"jsonrpc":"2.0","method":"notifications/progress","params":{"progressToken":"dep-1","progress":1,"total":4,"message":"pre-flight"}}

DATA (stream 1)
event: message
data: {"jsonrpc":"2.0","method":"notifications/message","params":{"level":"info","logger":"deploy","data":"Pre-flight checks passed (3 of 3). Target environment not specified."}}

DATA (stream 1, END_STREAM)
event: message
data: {"jsonrpc":"2.0","id":1,"result":{"resultType":"input_required","inputRequests":{"confirm_target":{"method":"elicitation/create","params":{"mode":"form","message":"billing@2.14.0 passed pre-flight. Which environment should receive it?","requestedSchema":{"type":"object","properties":{"environment":{"type":"string","enum":["staging","production"]},"drain_first":{"type":"boolean","default":true}},"required":["environment"]}}}},"requestState":"v1.eyJzdmMiOiJiaWxsaW5nIiwiaW1nIjoic2hhMjU2OjlmM2MxYSIsInN1YiI6ImFhcm9uIiwiZXhwIjoxNzkyMzI3NDAwfQ.k3Qm…","_meta":{"io.modelcontextprotocol/serverInfo":{"name":"deployer","version":"3.2.0"}}}}
```

Stream 1 is now closed on both sides. **The server has stopped.** It kept nothing in
memory: everything it needs to resume (service, resolved image, who asked, an expiry) is
inside `requestState`, signed so the client cannot tamper with it. The SSE `event:` field
is always `message`; the message type is inside the JSON. There are no `id:` lines,
because resumability was removed.

### Meanwhile, in the client

The client renders the form, the user picks `production` and leaves `drain_first` on.
Could be seconds, could be an hour. No connection is held open while waiting.

### Stream 3 → `tools/call` (attempt 2, with answers)

```http
HEADERS (stream 3)
:method: POST
:path: /mcp
:authority: deployer.example.net
content-type: application/json
accept: application/json, text/event-stream
authorization: Bearer eyJhbGciOi…
mcp-protocol-version: 2026-07-28
mcp-method: tools/call
mcp-name: deploy_service

DATA (stream 3, END_STREAM)
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "deploy_service",
    "arguments": { "service": "billing", "version": "2.14.0" },
    "inputResponses": {
      "confirm_target": {
        "action": "accept",
        "content": { "environment": "production", "drain_first": true }
      }
    },
    "requestState": "v1.eyJzdmMiOiJiaWxsaW5nIiwiaW1nIjoic2hhMjU2OjlmM2MxYSIsInN1YiI6ImFhcm9uIiwiZXhwIjoxNzkyMzI3NDAwfQ.k3Qm…",
    "_meta": {
      "io.modelcontextprotocol/protocolVersion": "2026-07-28",
      "io.modelcontextprotocol/clientInfo": { "name": "study-client", "version": "0.1" },
      "io.modelcontextprotocol/clientCapabilities": { "elicitation": { "form": {} } },
      "io.modelcontextprotocol/logLevel": "info",
      "progressToken": "dep-2"
    }
  }
}
```

Notes: new JSON-RPC `id` (the spec requires it; this is a new request). Same method and
arguments. `inputResponses` keys match the `inputRequests` keys. `requestState` is
echoed byte for byte. This POST may land on a different server instance; it does not
matter.

### Stream 3 ← SSE response, ends with the real result

```http
HEADERS (stream 3)
:status: 200
content-type: text/event-stream
cache-control: no-cache
x-accel-buffering: no

DATA (stream 3)
event: message
data: {"jsonrpc":"2.0","method":"notifications/message","params":{"level":"info","logger":"deploy","data":"Request state verified (issued 41 s ago, same principal). Resuming billing@2.14.0 → production."}}

DATA (stream 3)
event: message
data: {"jsonrpc":"2.0","method":"notifications/message","params":{"level":"info","logger":"deploy","data":"Draining 6 instances…"}}

DATA (stream 3)
event: message
data: {"jsonrpc":"2.0","method":"notifications/progress","params":{"progressToken":"dep-2","progress":2,"total":4,"message":"drained"}}

DATA (stream 3)
event: message
data: {"jsonrpc":"2.0","method":"notifications/message","params":{"level":"info","logger":"deploy","data":"Rolling out sha256:9f3c1a… (3/6 healthy)"}}

DATA (stream 3)
event: message
data: {"jsonrpc":"2.0","method":"notifications/progress","params":{"progressToken":"dep-2","progress":3,"total":4,"message":"rolling"}}

DATA (stream 3)
event: message
data: {"jsonrpc":"2.0","method":"notifications/message","params":{"level":"info","logger":"deploy","data":"6/6 healthy. Previous revision retired."}}

DATA (stream 3)
event: message
data: {"jsonrpc":"2.0","method":"notifications/progress","params":{"progressToken":"dep-2","progress":4,"total":4,"message":"done"}}

DATA (stream 3, END_STREAM)
event: message
data: {"jsonrpc":"2.0","id":2,"result":{"resultType":"complete","content":[{"type":"text","text":"Deployed billing 2.14.0 to production. 6/6 instances healthy."}],"structuredContent":{"service":"billing","version":"2.14.0","environment":"production","healthy":6},"isError":false,"_meta":{"io.modelcontextprotocol/serverInfo":{"name":"deployer","version":"3.2.0"}}}}
```

Shape of the whole conversation:

```
stream 1:  → call ·· ← log, progress, log, input_required ┤ closed
           (user answers; nothing open)
stream 3:  → call+answers ·· ← log, log, progress, log, progress, log, progress, result ┤ closed
```

---

## B. 2025-11-25: server-initiated elicitation (the shape you sketched)

Here the server *can* send a JSON-RPC request to the client on the open stream, keep
working, and collect the answer later. This requires server-side state: the pending
request, the session it belongs to, and some way for the answer POST to find the same
instance. Assume `initialize` already ran and the server minted a session.

### Stream 1 → `tools/call`

```http
HEADERS (stream 1)
:method: POST
:path: /mcp
content-type: application/json
accept: application/json, text/event-stream
authorization: Bearer eyJhbGciOi…
mcp-protocol-version: 2025-11-25
mcp-session-id: 7c1f4b9e-d2a0-4c58-9b3e-1f0a6c2d8e47

DATA (stream 1, END_STREAM)
{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"deploy_service","arguments":{"service":"billing","version":"2.14.0"},"_meta":{"progressToken":"dep-1"}}}
```

### Stream 1 ← SSE response (stays open across the question)

```http
HEADERS (stream 1)
:status: 200
content-type: text/event-stream
cache-control: no-cache

DATA (stream 1)
id: 7c1f-0001
event: message
data: {"jsonrpc":"2.0","method":"notifications/message","params":{"level":"info","logger":"deploy","data":"Resolved billing@2.14.0 to image sha256:9f3c1a…"}}

DATA (stream 1)
id: 7c1f-0002
event: message
data: {"jsonrpc":"2.0","method":"notifications/message","params":{"level":"info","logger":"deploy","data":"Pre-flight checks passed (3 of 3)."}}

DATA (stream 1)                                   ← a REQUEST from server to client
id: 7c1f-0003
event: message
data: {"jsonrpc":"2.0","id":101,"method":"elicitation/create","params":{"mode":"form","message":"Which environment should receive billing@2.14.0?","requestedSchema":{"type":"object","properties":{"environment":{"type":"string","enum":["staging","production"]},"drain_first":{"type":"boolean","default":true}},"required":["environment"]}}}

DATA (stream 1)                                   ← work continues while waiting
id: 7c1f-0004
event: message
data: {"jsonrpc":"2.0","method":"notifications/message","params":{"level":"info","logger":"deploy","data":"Pre-pulling image on 6 nodes while waiting for confirmation…"}}

        … stream 1 stays open, idle apart from keepalive comments (": ping") …
```

### Stream 3 → the client's answer, as a JSON-RPC *response* in a new POST

```http
HEADERS (stream 3)
:method: POST
:path: /mcp
content-type: application/json
accept: application/json, text/event-stream
authorization: Bearer eyJhbGciOi…
mcp-protocol-version: 2025-11-25
mcp-session-id: 7c1f4b9e-d2a0-4c58-9b3e-1f0a6c2d8e47

DATA (stream 3, END_STREAM)
{"jsonrpc":"2.0","id":101,"result":{"action":"accept","content":{"environment":"production","drain_first":true}}}
```

### Stream 3 ← acknowledgement only

```http
HEADERS (stream 3, END_STREAM)
:status: 202
```

The 202 carries nothing. The server matched `id: 101` to the request it is still
holding for session `7c1f…`, handed the answer to the worker that is still running
behind stream 1, and that worker carries on.

### Stream 1 ← continues, ends with the result

```http
DATA (stream 1)
id: 7c1f-0005
event: message
data: {"jsonrpc":"2.0","method":"notifications/message","params":{"level":"info","logger":"deploy","data":"Confirmed: production. Draining 6 instances…"}}

DATA (stream 1)
id: 7c1f-0006
event: message
data: {"jsonrpc":"2.0","method":"notifications/progress","params":{"progressToken":"dep-1","progress":2,"total":4}}

DATA (stream 1)
id: 7c1f-0007
event: message
data: {"jsonrpc":"2.0","method":"notifications/message","params":{"level":"info","logger":"deploy","data":"6/6 healthy. Previous revision retired."}}

DATA (stream 1, END_STREAM)
id: 7c1f-0008
event: message
data: {"jsonrpc":"2.0","id":1,"result":{"content":[{"type":"text","text":"Deployed billing 2.14.0 to production. 6/6 instances healthy."}],"isError":false}}
```

Shape of the whole conversation:

```
stream 1:  → call ·· ← log, log, REQUEST(101), log ········· log, progress, log, result ┤
stream 3:                                       → response(101) ← 202 ┤
```

Notes: `id:` lines are present because 2025 streams are resumable. The server-side
costs are visible: the worker and the pending request `101` live in memory on one
instance; the POST on stream 3 must reach that instance (sessions plus sticky routing,
or a shared store); if the client never answers, something has to time the worker out.
Those costs are what 2026-07-28 removed by making the server say "stop, ask, retry"
instead.

---

## What to notice across the two

| | 2025-11-25 (server request) | 2026-07-28 (MRTR) |
|---|---|---|
| Who asks the question | server, as a JSON-RPC request on the stream | server, as a result that ends the stream |
| Does the tool keep running while the user thinks | yes | no |
| How the answer travels | POST of a JSON-RPC *response*, 202 back | retry of the original request with `inputResponses` |
| Server state between question and answer | pending request + worker, per session | none; everything is in `requestState` |
| Connections held open while waiting | one | zero |
| Routing requirement | answer must reach the same instance | any instance |
| Stream resumability | `id:` + `Last-Event-ID` | removed; client re-issues |
