# OpenAI Agents SDK Starter

Learning project exploring the OpenAI Agents SDK (Python).

**Goal**: Understand how the Agent lifecycle works, how tools are called, and how to integrate MCP servers and other agents.

## Quick Start

### Setup

```bash
# Clone or navigate to this directory
cd experiments/01-openai-agents

# Create virtual environment (using uv)
uv venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install dependencies
uv sync
# Or with pip: pip install -e .

# Copy and configure environment
cp .env.example .env
# Edit .env with your OPENAI_API_KEY
```

### Run Scripts

Each script is self-contained and runnable:

```bash
python 01_hello_agent.py
python 02_function_tools.py
python 03_mcp_tools.py
python 04_handoffs_and_agents_as_tools.py
python 05_streaming_and_tracing.py
```

## Scripts Overview

### `01_hello_agent.py`
**What it teaches**: Basic Agent and Runner lifecycle.

- Minimal example: create an Agent with a simple task
- Use `Runner.run_sync()` to execute the agent
- Print the final output
- Key concepts: Agent definition, Runner patterns, synchronous execution

### `02_function_tools.py`
**What it teaches**: Tool definition and invocation within an agent.

- Define tools using `@function_tool` decorator
- Examples: `get_time()`, `calculator(operation, a, b)`
- Agent calls tools automatically when needed
- Print the run's items/trace to see the tool-calling loop
- Key concepts: Tool schema generation, tool calling loop, step-by-step execution

### `03_mcp_tools.py`
**What it teaches**: MCP server integration.

- Connect to an MCP server using `MCPServerStdio` (or HTTP alternatives)
- Example servers: `mcp-server-fetch`, `mcp-server-time`, filesystem
- Agent discovers and calls MCP tools
- Show available tools and execution traces
- Key concepts: MCP discovery, stdio vs. HTTP, tool transport, server lifecycle
- **Questions to explore**: How does tool schema flow from MCP → OpenAI? How are errors handled? What's the latency?

### `04_handoffs_and_agents_as_tools.py`
**What it teaches**: Agent composition and delegation.

- **Handoffs**: One agent delegates to another (built-in handoff pattern)
- **Agents-as-tools**: Use `agent.as_tool()` to call an agent like a function
- Compare: When is each pattern appropriate?
- Examples: Triage agent → specialist agents; multi-agent workflows
- Key concepts: Agent roles, delegation, composability, tool abstraction

### `05_streaming_and_tracing.py`
**What it teaches**: Real-time feedback and observability.

- Use `Runner.run_streamed()` to stream events as they occur
- Print event details (thought, tool calls, results) in real-time
- Built-in tracing dashboard (mention where to find it)
- Understand latency and intermediate steps
- Key concepts: Streaming patterns, event types, tracing/observability

## Key Concepts

### Agent
The core entity: takes a task/prompt, maintains state, and runs a tool-calling loop.

### Runner
Executes an Agent. Two main patterns:
- `Runner.run_sync()` – blocks until complete; returns final state
- `Runner.run_streamed()` – yields events as they happen

### Tools
Tools are functions the agent can call to solve tasks:
- **Function tools**: Defined with `@function_tool` in Python code
- **MCP tools**: Fetched from an MCP server; same interface to the agent

### MCP Servers
Model Context Protocol servers expose tools to agents over stdio or HTTP.
- **Stdio**: Subprocess communication (lower latency, local only)
- **HTTP**: Remote servers or easier deployment
- The SDK handles tool schema discovery and invocation.

### Handoffs
When one agent needs to transfer control to another (e.g., triage → specialist).
Built into the framework; agent can request a handoff, and the runner processes it.

### Agents as Tools
Call one agent from another by wrapping it with `agent.as_tool()`. Treated like any other tool.

### Tracing & Observability
The SDK provides built-in tracing of:
- Prompts sent to LLM
- Tool calls and results
- Agent state transitions
- Optional dashboard for inspection

## Things to Try / Learning Follow-ups

- [ ] Modify a task prompt and see how the agent's tool calls change
- [ ] Add a new function tool and test the agent's ability to discover and use it
- [ ] Connect to an MCP server (e.g., `mcp-server-fetch`) and have the agent fetch web content
- [ ] Chain multiple agents with handoffs; trace the control flow
- [ ] Stream a long-running task and watch events arrive in real-time
- [ ] Inspect the tracing dashboard; correlate events with tool latency
- [ ] Try different models (e.g., `gpt-4-turbo` vs `gpt-4o`) and compare tool-calling behavior
- [ ] What happens if a tool fails? How does the agent recover?
- [ ] Implement a custom MCP server (simple example: time + math) and integrate it
- [ ] Compare handoff vs. agent-as-tool: which is more efficient for your use case?

## Useful Links

- [OpenAI Agents SDK Docs](https://openai.github.io/openai-agents-python/)
- [Model Context Protocol Spec](https://spec.modelcontextprotocol.io/)
- [MCP Official Servers](https://github.com/modelcontextprotocol/servers)
- [MCP HTTP Examples](https://spec.modelcontextprotocol.io/docs/concepts/transport)

## Notes

- Each script prints detailed logs/traces. Look for `[TRACE]` or `[TOOL_CALL]` markers.
- Environment variables are loaded from `.env` (which git ignores).
- Model defaults to `gpt-4o`; override with `OPENAI_MODEL` env var.
- Some scripts may require additional dependencies (e.g., MCP servers). See comments in the script.
