# Agent as tool: what elicitation looks like when the tool is itself an agent

Design note for walkthrough steps 2.8–2.9 and Track B3. Written 2026-10-18 after the
`weather` round trip in trace step 6.

## The stack for one hop

```
 human ──(chat UI)── agent A ──(LLM API)── A's model
                        │
                        └──(MCP Streamable HTTP)── MCP server B ── B's own agent loop ── B's LLM, B's tools, maybe C…
```

MCP does not know B is an agent. The only standard way for B to ask anything is
elicitation, and B's "user" is A's harness. Whether A answers itself or escalates to the
human is A's business; B never finds out.

## Sequence

1. Human → A: "tell me the weather". A's model emits a `function_call` for `weather_agent`; the LLM response ends.
2. A's harness → B: `tools/call`. B runs its loop; B's model needs a city; B's tool returns `Elicit`; B's MCP layer ends the response with `input_required` + `elicitation/create` + sealed `requestState`.
3. A holds two unanswered "I can't finish without X" messages, one from B (MCP) and one from its own model (LLM API). Same shape, opposite directions.
4. A decides:
   - **Answer itself**: from conversation context or by asking its own model; retry B with `inputResponses` + state. Human unaware.
   - **Escalate, UI route**: render the form outside the model's view, wait, retry B.
   - **Escalate, model route**: return the question to the model as the tool output; model asks the human; next turn the model re-calls the tool with the answer as an argument (fresh call, old `requestState` discarded).
5. B resumes on the retry, finishes, returns the result → A's model → human.

No connection is held open anywhere while the human thinks.

## Where it bites

- **B's state across the gap.** `requestState` carries resolver outcomes, not B's transcript. Options: serialise the transcript into the sealed state (small loops only); server-side store + handle in the state (reintroduces a store); re-run from scratch with the answer (simplest; what the SDK does with the tool body).
- **TTL vs human latency.** SDK default seal expiry is 600 s. A slow human → `-32602` on retry → A must start over. Raise the TTL or build the fresh-call fallback.
- **Nesting.** B calling C that elicits: B re-wraps C's question as its own `Elicit`, with C's `requestState` inside B's. Questions climb one hop at a time; answers descend as a chain of retries. Shortest TTL wins.
- **Capabilities are the contract.** A must declare `elicitation.form` to be asked. A headless harness that will not answer must not declare it; B then fails cleanly (`isError: true`, as in trace 6d).
- **No token streaming.** B may push progress/log notifications onto A's response stream; B's generated text arrives only in the final result.

## Protocol choice

- Short interactions: agent-as-MCP-tool with MRTR; every server stateless.
- Long-running or chatty: MCP tasks extension (task handle, `tasks/get` polling, `tasks/update` for input) or A2A (tasks with an `input-required` state, streamed status updates, push notifications). The two are converging.

## Experiment to run (step 2.9)

Build B as an MCP server whose `weather_agent` tool runs an OpenAI Responses loop with its
own tools, and A as a harness that: declares `elicitation.form`; on `input_required`
first tries to answer from its own conversation; otherwise prints the question, reads
stdin, and retries. Capture the whole thing with `trace_session.py`-style narration on
both hops. Then repeat with the tasks extension and compare.
