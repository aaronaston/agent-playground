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
2. **MCP transports** – Streamable HTTP optionally uses SSE for server-to-client messages.
3. **A2A** – streaming task updates and push notifications.

Topics:
- Wire format: `text/event-stream`, `data:` / `event:` / `id:` fields, reconnection with `Last-Event-ID`.
- SSE vs. WebSockets vs. plain chunked HTTP.
- Pitfalls: proxy buffering, timeouts, idle connections.

Hands-on:
- [ ] Read a raw stream with curl.
- [ ] Implement a tiny SSE endpoint.
- [ ] Capture a Messages API stream.
- [ ] Capture an MCP Streamable HTTP session.

Done when: I can explain each event in a captured stream and why SSE (not WebSockets) is used.

### B2. MCP
- [ ] Transports: stdio vs. Streamable HTTP; why the old HTTP+SSE transport was deprecated (single endpoint, session IDs, resumability).
- [ ] Tools, resources, prompts; capability negotiation.
- [ ] Function tools vs. MCP tools: when to use which.

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
2. Rung 1 chatbots for all four vendors.
3. Rung 2 agents: OpenAI (finish 01), Anthropic, LangGraph, Microsoft.
4. Rest of Track B: MCP transports and A2A.
5. Track C (Keycloak).
6. Track D (enterprise-managed authorization).
7. Revisit the hypothesis and write conclusions.

## Glossary

| Term | Meaning |
|---|---|
| SSE | Server-Sent Events: one-way server-to-client stream over HTTP (`text/event-stream`) |
| MCP | Model Context Protocol: agent-to-tool protocol |
| A2A | Agent2Agent protocol: agent-to-agent protocol |
| Streamable HTTP | Current MCP HTTP transport; single endpoint, optional SSE |
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
