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
| 00 | Protocols | SSE, WebSockets, HTTP/1.1 vs HTTP/2 warm-up ([experiments/00-protocols](experiments/00-protocols)) | ✅ Done |
| 01 | OpenAI | Chatbot (Responses API) + Agents SDK agent | 🚧 In Progress |
| 02 | Anthropic | Chatbot (Messages API) + Claude Agent SDK agent | 📋 Planned |
| 03 | LangGraph | Chatbot + agent graph | 📋 Planned |
| 04 | Microsoft Agent Framework | Chatbot + agent | 📋 Planned |
| 05+ | MCP/A2A, Keycloak OAuth, enterprise-managed auth | See the study guide | 📋 Planned |

**Start here:** [WALKTHROUGH.md](WALKTHROUGH.md) says what to do next and where I am. [STUDY_GUIDE.md](STUDY_GUIDE.md) is the curriculum behind it. [QUESTIONS.md](QUESTIONS.md) logs the questions that changed the plan.

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
