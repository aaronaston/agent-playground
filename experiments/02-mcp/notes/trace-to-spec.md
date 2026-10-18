# Step 2.1: the trace, line by line, against the 2026-07-28 spec

Reading guide and map for walkthrough step 2.1. Open two things side by side: the trace
in [`../captures/streamable-http-session.txt`](../captures/streamable-http-session.txt)
and the spec pages linked below. The job is to find, for every message in the trace, the
sentence in the spec that caused it.

Base URL for all links: `https://modelcontextprotocol.io/specification/2026-07-28`.

## Reading order (about two hours)

| # | Page | Read for | Minutes |
|---|---|---|---|
| 1 | `/basic/index` | Messages (request / result / error / notification), `resultType`, error-code ranges, **Statelessness**, `_meta` reserved keys and the per-request fields table | 25 |
| 2 | `/basic/versioning` | No handshake; `UnsupportedProtocolVersionError`; `server/discover`; the modern / legacy / dual-era terminology and the compatibility matrix | 15 |
| 3 | `/basic/transports/streamable-http` | One endpoint, POST only; JSON vs SSE response; `Mcp-Method` / `Mcp-Name` mirroring and validation; cancellation = closing the stream; 405 for GET | 25 |
| 4 | `/basic/patterns/progress` | `progressToken`, `notifications/progress` fields and rules | 5 |
| 5 | `/basic/patterns/subscriptions` | `subscriptions/listen`, the filter, the acknowledgement, `subscriptionId`, how a stream ends | 10 |
| 6 | `/basic/patterns/mrtr` | `InputRequiredResult`, `inputRequests` / `inputResponses`, `requestState` and its security rules, client retry rules | 20 |
| 7 | `/server/tools` | `tools/list` and `tools/call` results, `outputSchema` / `structuredContent`, `ttlMs` / `cacheScope`, protocol vs tool-execution errors, stateful tools via handles | 20 |
| 8 | `/changelog` | Once, to know what an older server would show you and why each thing was removed | 10 |

Skip for now: authorization (Track C), resources and prompts (step 2.3), the tasks
extension (2.7), stdio (2.2).

## The map

Each row is one thing in the trace. "Rule" is the spec sentence, paraphrased, with the
page it lives on.

### Part 1: discovery, listing, a streamed call (conn #1)

| Trace | What you saw | Rule (page) |
|---|---|---|
| Every request | `params._meta` with `protocolVersion`, `clientInfo`, `clientCapabilities`, `logLevel` | Per-request protocol fields table: `protocolVersion` and `clientCapabilities` are required on every request; `clientInfo` SHOULD be sent; `logLevel` opts into log messages (`/basic/index` → `_meta`) |
| Every request | `MCP-Protocol-Version: 2026-07-28` header | MUST be present on every POST and MUST match `_meta`; mismatch is `400` + `HeaderMismatch` (`/basic/transports/streamable-http` → Protocol Version Header) |
| Every request | `Mcp-Method:` header; `Mcp-Name:` on `tools/call` | Required standard request headers, mirrored from `method` and `params.name` so intermediaries can route without parsing JSON (same page → Standard Request Headers) |
| Every request | `Accept: application/json, text/event-stream` | Client MUST list both; the server picks per request (same page → Sending Messages) |
| Three requests, one connection | `[conn #1] request #3 on this connection` | Statelessness: servers MUST NOT rely on prior requests over the same connection for context; the connection is not a session (`/basic/index` → Statelessness) |
| 1 `server/discover` | plain JSON, `supportedVersions`, `capabilities`, `_meta.serverInfo` | Servers MUST implement it; clients MAY call it first or just send requests and handle `-32022` (`/basic/versioning` → Protocol Version Negotiation) |
| 1, 2 results | `resultType: "complete"` | Every result MUST carry `resultType`; absent means `complete` only when talking to older servers (`/basic/index` → ResultType) |
| 1, 2 results | `_meta.io.modelcontextprotocol/serverInfo` | Servers SHOULD identify themselves in every result's `_meta`, self-reported, display only (`/basic/index` → Per-response protocol fields) |
| 2 `tools/list` | `content-type: application/json`, no stream | Server returns a single JSON object or an SSE stream; its choice (`/basic/transports/streamable-http` → Sending Messages, item 6) |
| 2 result | `ttlMs: 0`, `cacheScope: "private"`, deterministic order | Caching hints on list results; SHOULD return tools in a deterministic order; the set MUST NOT vary per connection (`/server/tools` → Capabilities, Listing Tools) |
| 2 result | `inputSchema`, `outputSchema` | `inputSchema` MUST be a valid JSON Schema object, default dialect 2020-12; `outputSchema` optional (`/server/tools` → Tool) |
| 3 request | `"progressToken": "p1"` in `_meta` | Opts the request into progress notifications; token MUST be unique across active requests (`/basic/patterns/progress`) |
| 3 response | `content-type: text/event-stream`, `x-accel-buffering: no`, chunked | SSE stream scoped to this request; servers SHOULD send `X-Accel-Buffering: no` (`/basic/transports/streamable-http` → Receiving Messages) |
| 3 events #1, #3, #5 | `notifications/message` level `info` | Log messages, sent only because the request carried `logLevel`; the capability is deprecated as of this revision (`/basic/index` → `_meta`; changelog) |
| 3 events #2, #4 | `notifications/progress` with `progressToken`, `progress` 1 then 2, `total` 2, `message` | `progress` MUST increase; `total` and `message` optional; MUST stop after completion (`/basic/patterns/progress`) |
| 3 events, all | `event: message` | SSE event type is unused; the message type is the JSON-RPC `method` (`/basic/transports/streamable-http`) |
| 3 event #6 | the result, then the chunked body ends | Notifications MUST relate to the originating request; the final response SHOULD terminate the stream (same page → Receiving Messages) |
| 3 result | `content[]`, `structuredContent`, `isError: false` | Tool result shape; `structuredContent` MUST conform to `outputSchema`; a text copy SHOULD accompany it (`/server/tools` → Tool Result) |
| nowhere | no `id:` lines in any stream | Resumable streams via `Last-Event-ID` are not supported (same page → Receiving Messages, last line) |

### Part 2: rejections

| Trace | What you saw | Rule (page) |
|---|---|---|
| 4a no `Mcp-Method` | `400`, `-32020` HeaderMismatch | Servers MUST reject when a required standard header is missing or mismatched (`/basic/transports/streamable-http` → Server Validation) |
| 4b version `2027-01-01` | `400`, `-32022`, `data.supported` and `data.requested` | Unknown or unsupported version MUST get `UnsupportedProtocolVersionError` listing supported versions; the client SHOULD retry with one (`/basic/versioning`) |
| 4c `GET` | `405` | The endpoint supports POST; a GET from an older client SHOULD get `405` (`/basic/transports/streamable-http` → Earlier Streamable HTTP Revisions) |
| probe a) no `_meta` | `400`, `-32602` | A request missing a required `_meta` field is malformed: `-32602`, HTTP `400` (`/basic/index` → Per-request protocol fields) |
| probe b) `weather` with `clientCapabilities: {}` | `400`, `-32021`, `data.requiredCapabilities: {elicitation: {form: {}}}` | A server MUST NOT rely on undeclared capabilities and MUST return `MissingRequiredClientCapabilityError` (`/basic/index` → Per-request protocol fields) |
| error codes seen | `-32020`, `-32021`, `-32022`, `-32602` | `-32020..-32099` reserved for the spec; `-32000..-32019` legacy, do not allocate (`/basic/index` → Error Codes) |

### Step 5: `subscriptions/listen` (conn #5, triggered from conn #6)

| Trace | What you saw | Rule (page) |
|---|---|---|
| 5 request | `params.notifications: {toolsListChanged: true}` | The filter; server MUST NOT send types not requested (`/basic/patterns/subscriptions` → Opening a Stream) |
| 5 event #1 | `notifications/subscriptions/acknowledged`, `_meta.subscriptionId: 5`, the filter echoed | MUST be the first message; `subscriptionId` equals the JSON-RPC id of the listen request; the echoed filter is the subset honoured (→ Acknowledgment) |
| 5 quiet for 2 s | nothing | A long-lived request is still request/response; the response is an open stream (`/basic/index` → Statelessness) |
| 5b on another connection | `announce_change` result, plain JSON, on conn #6 | Notifications on a request's own stream MUST relate to that request, so the change notification cannot go here (`/basic/transports/streamable-http` → Receiving Messages) |
| 5 event #2 | `notifications/tools/list_changed` with `subscriptionId: 5` | Servers with `listChanged` SHOULD notify listeners; every notification on the stream carries `subscriptionId` (`/server/tools` → List Changed Notification; `/basic/patterns/subscriptions` → Receiving Notifications) |
| client closes conn #5 | `[conn #5] closed by client` | Client cancels by closing the SSE stream; a server-initiated end would send a `subscriptions/listen` result first (→ Cancellation, Graceful Closure) |

### Step 6: MRTR (conns #7–#10)

| Trace | What you saw | Rule (page) |
|---|---|---|
| 6a result | `resultType: "input_required"`, plain JSON, HTTP 200 | `tools/call` MAY return an `InputRequiredResult`; the initial request is terminated (`/basic/patterns/mrtr` → Basic Workflow; `/server/tools` → Input Required Tool Results) |
| 6a `inputRequests` | one key `__main__:ask_city` → `elicitation/create`, `mode: form`, `requestedSchema` | Keys are server-assigned and unique within the request; values MUST be `ElicitRequest`, `CreateMessageRequest` or `ListRootsRequest` (→ Server Requirements 2) |
| 6a `inputRequests` present at all | only because the request declared `elicitation.form` | Servers MUST NOT send an input request the client has not declared support for (→ Server Requirements 7; probe b) is the failure case) |
| 6a `requestState` | 351 opaque characters | Opaque to the client; MUST be treated by the server as attacker-controlled and integrity-protected when it affects logic; SHOULD bind principal, expiry and originating request (→ Server Requirements 3–5) |
| 6b request | same method and arguments, new id, `inputResponses` keyed to match, `requestState` echoed | Client MUST construct the inputs, MUST echo `requestState` exactly, MUST use a different JSON-RPC id (→ Client Requirements 1–3) |
| 6b response | log line, then the real result | Each round is an independent request; the retry needs nothing beyond what it carries (→ Basic Workflow) |
| 6c tampered state | `400`, `-32602`, `data.reason: invalid_request_state` | Servers MUST reject state that fails verification (→ Server Requirements 4) |
| 6d decline | `200`, `isError: true`, readable message | Tool execution errors carry actionable text for the model; the spec leaves the decline outcome to the server (`/server/tools` → Error Handling) |

## Where the SDK and the spec's examples differ

Worth knowing so you do not "learn" an SDK quirk as protocol.

- **Unknown tool.** The tools page shows a protocol error (`-32602`, "Unknown tool"). The
  SDK returns a `200` with `isError: true` and the same text (probe c). Both are
  defensible; the spec's error-handling section says protocol errors are for things the
  model is unlikely to fix, and an unknown tool name arguably is one.
- **`tools/list` as JSON, `initialize` as SSE.** Which response shape the server picks is
  its choice per request. The 2026 SDK picks JSON when nothing will precede the result;
  the legacy path still streams even a one-event response.
- **`ttlMs: 0`.** The SDK sets the caching hint to zero by default, meaning "do not
  cache"; the spec's example uses five minutes. Configurable via `cache_hints`.
- **`-32602` for a bad `requestState`.** The MRTR page says protocol errors "with an
  appropriate error code"; the SDK chose Invalid params and added `data.reason`.

## Self-check (the step's done-when)

Say, in one sentence each, what replaced:

1. sessions and `Mcp-Session-Id`
2. the standalone `GET` stream
3. resumability and `Last-Event-ID`
4. server-initiated requests (`elicitation/create`, `sampling/createMessage`, `roots/list`)

<details><summary>Answers</summary>

1. Nothing at the protocol level: every request carries version, identity and capabilities in `_meta`, and anything that must span calls is an explicit handle the client passes back (a tool argument, or `requestState`).
2. `subscriptions/listen`: a POST whose response stream stays open and carries only the opted-in notification types, each tagged with the subscription id.
3. Nothing: a broken response stream loses the in-flight request and the client re-issues it with a new id.
4. MRTR: the server ends its response with `resultType: input_required`, the client answers by retrying the original request with `inputResponses` and the echoed `requestState`.

</details>

Then one more, from the changelog: why was each of the four removed? (Statelessness
behind a load balancer is the common answer; say it in your own words for each.)
