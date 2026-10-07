# Agent Playground

A personal learning project for exploring agent frameworks, MCP (Model Context Protocol), and agent-to-agent communication patterns.

## Purpose

This repo documents my journey through:
- How different agent frameworks work (APIs, abstractions, patterns)
- How agents access tools via MCP and direct integration
- How agents coordinate with other agents (handoffs, delegation, tool composition)

Each experiment is self-contained, reproducible, and heavily commented for learning.

## Experiments

| # | Framework | Topic | Status |
|---|-----------|-------|--------|
| 01 | OpenAI Agents SDK (Python) | Basics: Agent, Runner, function tools, MCP tools, handoffs, streaming | 🚧 In Progress |
| 02 | (Coming) | Anthropic Claude with Tools | 📋 Planned |
| 03 | (Coming) | Langgraph | 📋 Planned |
| 04 | (Coming) | Agent-to-agent patterns | 📋 Planned |

## Structure & Conventions

Each experiment lives in `experiments/XX-name/`:
- **README.md** – Setup, how to run scripts, key concepts, learning notes
- **pyproject.toml** – Python dependencies (for `uv` or pip)
- **.env.example** – Required environment variables (template)
- **Scripts** – Runnable Python files, numbered and progressive in complexity

### Quick start for any experiment

```bash
cd experiments/XX-name
uv venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
uv sync  # or: pip install -e .
cp .env.example .env
# Edit .env with your credentials
python 01_hello_agent.py  # or whichever script
```

## Learning Goals

- [ ] Understand agent lifecycle and tool-calling loops
- [ ] Explore MCP server integration options (stdio, HTTP, etc.)
- [ ] Compare function tools vs. MCP tools
- [ ] Learn agent handoff patterns
- [ ] Implement agent-as-tool composition
- [ ] Experiment with streaming and real-time feedback
- [ ] Understand guardrails, sessions, and safety patterns

---

See each experiment's README for deeper details.
