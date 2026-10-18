# Annotated: a streamed tool call and its follow-up (2026-10-18)

Raw capture: [`openai-tool-call-stream.txt`](openai-tool-call-stream.txt), from
`experiments/capture_tool_call.py` (OpenAI Responses API, `gpt-4.1-mini`, one tool
`get_weather`, prompt "What's the weather in Toronto right now? One sentence."). Two
complete HTTP exchanges, request bodies included. Cookie and account ids redacted.

## The shape

```
exchange 1  → POST  user message + tool definition
            ← SSE   created, in_progress,
                    output_item.added        {type: function_call, name: get_weather, call_id: call_EF4r…}
                    function_call_arguments.delta  x5   {"  city  ":"  Toronto  "}
                    function_call_arguments.done        {"city":"Toronto"}
                    output_item.done         status completed
                    completed                status completed, usage 48 in / 15 out
            stream closed. The model has stopped. Nothing is waiting server-side.

client      runs get_weather("Toronto") itself -> {"temp_c": 11, "conditions": "overcast, light wind"}

exchange 2  → POST  user message + the function_call item + a function_call_output item
                    (the whole conversation again; no previous_response_id)
            ← SSE   created, in_progress, output_item.added {type: message},
                    content_part.added, output_text.delta x20, output_text.done,
                    content_part.done, output_item.done,
                    completed                usage 91 in / 22 out
```

## Things to notice

- **Exchange 1 ends with `status: completed`, not something like "waiting".** From the
  API's point of view the response is finished; it just happens to end in a request for
  work rather than in text. That is the MRTR pattern exactly: the 2026 MCP server ends its
  response with `resultType: "input_required"` and stops. Same move, different vocabulary.
- **The arguments stream too.** Five deltas build the JSON string `{"city":"Toronto"}` a
  token at a time, then `function_call_arguments.done` repeats it whole. A client that
  wants to show "calling get_weather…" early can act on `output_item.added`, which already
  carries the tool name and `call_id` before any arguments arrive.
- **`call_id` is the correlation key.** It appears in exchange 1's item and must be echoed
  on the `function_call_output` in exchange 2. Compare MCP: `inputRequests` keys and
  `requestState` play the same role.
- **Exchange 2 resends everything.** The user message, the model's own function_call item,
  and the output. The server kept nothing between the two calls (the API can, via
  `previous_response_id`, but this capture deliberately does not use it). Input tokens
  went from 48 to 91, which is the cost of statelessness.
- **Two independent HTTP exchanges, two TTFBs** (1.8 s and 1.5 s). A tool call always
  costs at least two model turns; the tool itself ran in between on the client, outside
  any HTTP connection to the API.
- **`strict: true` on the tool** is why the arguments are guaranteed to match the schema.
  MCP tools have `inputSchema` for the same job, validated by the server on receipt.

## Mapping onto MCP

| OpenAI Responses | MCP 2026-07-28 |
|---|---|
| `function_call` output item ends the response | `InputRequiredResult` ends the response |
| `call_id` | `inputRequests` key |
| client runs the tool | client runs the elicitation / sampling / roots lookup |
| new request with `function_call_output` | retry with `inputResponses` |
| conversation resent (or `previous_response_id`) | original params resent + `requestState` |
| `response.completed` with text | result with `resultType: "complete"` |

The one place the analogy bends: in the LLM case the *client* owns the tool and the
*model* asks for it; in MCP's MRTR the *server* owns the tool and asks the *client* for
input. The direction of "who needs whom" is reversed, but the wire pattern is identical.
