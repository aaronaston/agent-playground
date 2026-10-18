# Study Guide

A planning outline of what I want to learn, before diving in. Each topic has: key questions, resources, a hands-on experiment, and "done when" criteria. Check boxes as I go.

## Hypotheses to test

- OpenAI has two modes: in-process function calls/handoffs (threads/sessions) vs. out-of-process MCP and A2A. The shift to A2A/MCP is interprocess communication.
  - Test: in each framework, where is the process/trust boundary drawn for tools and for other agents?
  - Confirmed if: local tools/handoffs share state and process, while MCP/A2A cross a protocol boundary with separate auth and state.

---

## Track A – Frameworks: the two-rung ladder

Every framework gets the same ladder so they are comparable.

- **Rung 1 – Chatbot:** multi-turn conversation against the vendor's lowest-level API. No tools, no agent loop. Manual history, streamed tokens.
- **Rung 2 – Agent:** the vendor's agent framework on a common benchmark task: **one function tool + one MCP tool + one delegated agent/handoff**.
- Record what Rung 1 makes me build (state, history, request/response shape, streaming) vs. what Rung 2 adds (tool loop, handoffs, sessions, tracing).

| Vendor | Rung 1 (chatbot) | Rung 2 (agent) |
|---|---|---|
| OpenAI | Responses API (or Chat Completions) | Agents SDK (experiment 01 exists; add a chatbot script) |
| Anthropic | Messages API | Claude Agent SDK |
| LangGraph | Bare LangChain chat model in a simple graph | Graph with tool and agent nodes |
| Microsoft | Plain chat client (Azure OpenAI or OpenAI) | Microsoft Agent Framework |

Layout: one folder per vendor in `experiments/XX-name/`, with matching scripts (`01_chatbot.py`, `02_agent.py`, ...). Experiment 01 will gain a chatbot script, so its numbering shifts.

### A1. OpenAI
- [ ] Rung 1: Responses API chatbot with streaming.
- [ ] Rung 2: finish Agents SDK experiment (function tools, MCP, handoffs vs. agents-as-tools, streaming, tracing).

### A2. Anthropic
Fetch the Agent SDK overview first (https://code.claude.com/docs/en/agent-sdk/overview) to confirm the current API; SDKs change quickly.
- [ ] Rung 1 – Messages API: system prompt, manual history, streaming, then raw tool use to see the `tool_use` / `tool_result` loop by hand.
- [ ] Rung 2 – Claude Agent SDK: built-in tools, custom tools, MCP server config, subagents, permissions and hooks, sessions. Compare against the hand-written loop.

### A3. LangGraph
- [ ] Rung 1: chat model in a minimal graph.
- [ ] Rung 2: tool and agent nodes, state/checkpointing, MCP adapters.

### A4. Microsoft Agent Framework
- [ ] Rung 1: plain chat client (provider TBD: Azure OpenAI or OpenAI).
- [ ] Rung 2: Agent Framework agent, tools, MCP, multi-agent.

### Comparison table (fill in per vendor)

| Dimension | OpenAI | Anthropic | LangGraph | Microsoft |
|---|---|---|---|---|
| Lines of code (chatbot / agent) | | | | |
| Who owns the loop | | | | |
| State handling | | | | |
| Streaming API | | | | |
| MCP support | | | | |
| A2A support | | | | |
| Tracing / observability | | | | |

---

## Track B – Protocols

### B1. Transport foundations (start here): SSE
SSE appears at three layers, so learn it first and reference it elsewhere.
1. **LLM streaming** – every Rung 1 chatbot streams over SSE (OpenAI streaming events; Anthropic `message_start` / `content_block_delta`).
2. **MCP transports** – Streamable HTTP optionally uses SSE for multi-message responses (and `Last-Event-ID` resume in the 2025 revisions only; removed in 2026-07-28).
3. **A2A** – streaming task updates and push notifications.

Topics:
- Wire format: `text/event-stream`, `data:` / `event:` / `id:` fields, reconnection with `Last-Event-ID`.
- SSE vs. WebSockets vs. plain chunked HTTP.
- HTTP/1.1 vs. HTTP/2 warmup:
  - connection reuse and multiplexing
  - head-of-line blocking
  - request/response shape and streaming behavior
- Pitfalls: proxy buffering, timeouts, idle connections

Hands-on:
- [x] Read a raw stream with curl.
- [x] Implement a tiny SSE endpoint.
- [x] Compare one simple endpoint over HTTP/1.1 and HTTP/2.
- [ ] Compare the same streaming use case over SSE and WebSockets.
- [x] Capture an LLM API stream (OpenAI Responses, 2026-10-18; repeat with Anthropic Messages when a key exists).
- [x] Capture an MCP Streamable HTTP session.

Done when: I can explain each event in a captured stream and why SSE (not WebSockets) is used.

### B1 progress log
- [x] SSE wire format understood
- [x] `curl` can read a raw SSE stream
- [x] Tiny SSE endpoint implemented
- [x] HTTP/1.1 vs HTTP/2 differences observed
- [ ] SSE vs WebSockets differences observed
- [x] LLM streaming captured
- [ ] Can explain why SSE is used here instead of WebSockets

### B2. MCP: the protocol and its features
MCP is JSON-RPC 2.0 over a transport. Learn it against the **current revision (2026-07-28) first and only**; the 2025 family matters later, for recognising older servers, and is kept behind a `--legacy` flag in the experiments. Specs: https://modelcontextprotocol.io/specification/2026-07-28 and the changelog for each revision.

#### B2.1 Versions and the two families
- Five revisions, all still valid: 2024-11-05, 2025-03-26, 2025-06-18, 2025-11-25, 2026-07-28. Date-named; no central decommissioning.
- The real seam: the four 2025-and-earlier "handshake" versions (`initialize` round trip, `Mcp-Session-Id`) vs. the "modern" 2026-07-28 shape (stateless; version and capabilities in `_meta` on every request; `server/discover`).
- Feature lifecycle policy: Active / Deprecated / Removed, 12-month window. Deprecated registry: HTTP+SSE transport, Sampling, Roots, Logging, dynamic client registration.
- [ ] Read the 2025-03-26, 2025-06-18, 2025-11-25 and 2026-07-28 changelogs in order; note what each removed.
- [ ] Check which versions the Python SDK supports (`mcp_types.version`) and which one it picks by default.

#### B2.2 Message model
- Four JSON-RPC shapes: request (`id` + `method`), notification (`method`, no `id`), result, error. Every message is one SSE `data:` line or one stdio line.
- `method` is really a message type; `notifications/*` are events wearing an RPC costume (same as LSP).
- Correlation glue: `progressToken` in `_meta` ties `notifications/progress` to a request; `notifications/cancelled` carries `requestId`.
- 2026-07-28: every result has `resultType` (`complete` | `input_required`); `_meta` carries protocol version, client/server info, log level, OpenTelemetry trace context.
- [ ] Write out the full method list for 2025-06-18 and 2026-07-28 side by side; mark what was added, removed, or replaced.

#### B2.3 Transports
- stdio: newline-delimited JSON-RPC on stdin/stdout, stderr for logs. Still the default for local servers.
- Streamable HTTP: one endpoint, every client message is a POST, the response is either `application/json` or a `text/event-stream` that ends with the JSON-RPC result. "Streamable" is a capability of the response, not a mode of the connection.
- 2025 shape: `initialize` handshake, `Mcp-Session-Id`, optional GET stream for server-initiated messages, `Last-Event-ID` resumability.
- 2026-07-28 shape: no sessions, no handshake, no GET stream, no resumability (re-issue the request); `subscriptions/listen` is a POST whose response stream stays open for opted-in change notifications; `Mcp-Method` / `Mcp-Name` request headers.
- Why not WebSockets: plain HTTP keeps bearer-token headers, proxies, serverless and HTTP/2 multiplexing; a trivial server is just a JSON endpoint.
- Origin validation (403), localhost binding, DNS rebinding.
- [~] Build a minimal server with the Python SDK over stdio, then over Streamable HTTP. (HTTP done; stdio pending)
- [x] Drive the HTTP server with curl: a `tools/list`, a `tools/call`, and (2025 shape) an `initialize`; capture every header and body.
- [ ] Capture the same session from an SDK client and compare with the curl version.

#### B2.4 Server primitives
- **Tools**: `inputSchema` / `outputSchema` (JSON Schema 2020-12), `structuredContent`, annotations (readOnly, destructive, idempotent, openWorld), icons, tool-name guidance, deterministic `tools/list` ordering, `ttlMs` / `cacheScope` on list results. Validation errors are tool-execution errors (so the model can self-correct), not protocol errors.
- **Resources**: URIs, templates, `resources/read`; change notifications now via `subscriptions/listen` instead of `resources/subscribe`.
- **Prompts**: server-provided prompt templates with arguments; `prompts/get` returns messages.
- **Completion**: `completion/complete` for argument autocomplete.
- [ ] Add one of each to the sample server; call them from an SDK client and from Claude Code.
- [ ] Return structured output from a tool and watch how a client surfaces `structuredContent` vs. `content`.

#### B2.5 Server → client interaction
- **Progress** (`notifications/progress`) and **log messages** (`notifications/message`) ride on the originating request's response stream; log level is per-request via `_meta` in 2026-07-28.
- **Elicitation**: server asks the user for input. Form mode (schema-driven, enums, defaults) and URL mode (out-of-band browser flow).
- **Sampling**: server asks the client's LLM to generate (with `tools` / `toolChoice` since 2025-11-25). Deprecated in 2026-07-28; migration is "call the LLM provider directly".
- **Roots**: client-exposed filesystem roots. Deprecated; pass paths as tool arguments instead.
- **MRTR (Multi Round-Trip Requests)**: the 2026-07-28 replacement for all server-initiated requests. Server returns `resultType: "input_required"` with `inputRequests`; client retries the original request with `inputResponses`. `requestState` carries server correlation.
- **Cancellation**: `notifications/cancelled`; a dropped HTTP connection is *not* a cancel.
- [x] Implement a long-running tool that emits progress and log messages; watch them arrive before the result.
- [ ] Implement an elicitation (form mode) and trace the round trip on the wire, once as a 2025-style server-initiated request and once as MRTR.
- [ ] Try sampling against a 2025-era client to see what is being deprecated and why.

#### B2.6 Extensions and long-running work
- Extensions field in capabilities; the tasks extension (`io.modelcontextprotocol/tasks`): server returns a task handle, client polls `tasks/get`, sends input with `tasks/update`.
- [ ] Wrap the long-running tool from B2.5 as a task and poll it.

#### B2.7 Function tools vs. MCP tools
- In-process function tools share state and process; MCP crosses a protocol boundary with separate auth and lifecycle (ties to the hypothesis at the top).
- [ ] Decision table: when a function tool, when an MCP server, when A2A.

Done when: I can read a captured MCP session and name every message, say which revision it is, and explain what the 2026-07-28 revision removed and why.

### B2 progress log
- [ ] Changelogs read; two families understood
- [ ] Minimal server running over stdio and Streamable HTTP
- [ ] Wire captures: curl and SDK, both families
- [ ] Tools, resources, prompts, completion implemented and called
- [x] Progress and log messages observed mid-request
- [ ] Elicitation round trip traced (server-initiated and MRTR)
- [ ] Sampling tried and its deprecation understood
- [ ] Task extension tried
- [ ] Decision table written

### B3. A2A
- [ ] Agent cards, tasks, streaming and push notifications.
- [ ] Decision table: in-process handoff vs. MCP vs. A2A.

---

## Track C – MCP authorization with Keycloak (OAuth 2)

Primer first: OAuth 2.1 authorization code + PKCE, client credentials, resource indicators.

Questions:
- **RFC 9728** (Protected Resource Metadata): how does an MCP server advertise its authorization server? (`WWW-Authenticate` header, `.well-known`.)
- Is 9728 used with **RFC 8414** (Authorization Server Metadata)? Likely yes: 9728 points to the issuer, 8414/OIDC discovery describes endpoints. Verify in spec and Keycloak.
- **RFC 8707** (Resource Indicators): how is a token audience-bound to one MCP server?
- **RFC 8693** (Token Exchange): how does an agent get a suitable token for a downstream server?
- `subject_token` vs. `actor_token`: delegation vs. impersonation; the `act` claim.

Hands-on:
- [ ] Run Keycloak in Docker; protect a small MCP server.
- [ ] Walk the discovery flow with curl, then with an SDK client.
- [ ] Do a token exchange; inspect the JWTs.
- [ ] Note Keycloak gaps (token exchange, resource indicators).

---

## Track D – Enterprise-Managed Authorization (research)

- [ ] Read the MCP Enterprise-Managed Authorization extension and the ID-JAG draft.
- [ ] What problem does it solve (IdP-controlled access, no per-server consent prompts)?
- [ ] Is ID-JAG a return from 8693 token exchange to the RFC 7523 JWT bearer grant? Draw the flow.
- [ ] Compare trust and who does the exchange vs. plain 8693.
- [ ] Why is it an emerging standard for AI agents?

Output: a sequence diagram and a comparison table of 9728 discovery, 8693 exchange, and ID-JAG + 7523.

---

## Suggested order

1. Track B1: SSE and basic LLM streaming.
2. Track B2: MCP protocol and features (while the protocol questions are fresh; its first hands-on closes B1's last checkbox).
3. Rung 1 chatbots for all four vendors.
4. Rung 2 agents: OpenAI (finish 01), Anthropic, LangGraph, Microsoft.
5. Track B3: A2A.
6. Track C (Keycloak).
7. Track D (enterprise-managed authorization).
8. Revisit the hypothesis and write conclusions.

## Glossary

| Term | Meaning |
|---|---|
| SSE | Server-Sent Events: one-way server-to-client stream over HTTP (`text/event-stream`) |
| MCP | Model Context Protocol: agent-to-tool protocol |
| A2A | Agent2Agent protocol: agent-to-agent protocol |
| Streamable HTTP | Current MCP HTTP transport; single endpoint, optional SSE |
| Elicitation | MCP: server asks the user for input (form mode or URL mode) |
| Sampling | MCP: server asks the client's LLM to generate; deprecated in 2026-07-28 |
| MRTR | Multi Round-Trip Requests: 2026-07-28 pattern where a result says `input_required` and the client retries with answers |
| SEP | Specification Enhancement Proposal: how MCP changes are proposed |
| RFC 9728 | OAuth Protected Resource Metadata |
| RFC 8414 | OAuth Authorization Server Metadata |
| RFC 8707 | Resource Indicators for OAuth 2.0 |
| RFC 8693 | OAuth 2.0 Token Exchange |
| RFC 7523 | JWT bearer authorization grant |
| ID-JAG | Identity Assertion JWT Authorization Grant (enterprise-managed authorization) |
| subject_token / actor_token | Token exchange inputs: who is represented / who is acting |

## Open questions

- Microsoft chatbot provider: Azure OpenAI or OpenAI?
- Single guide file vs. one per track (currently single).
