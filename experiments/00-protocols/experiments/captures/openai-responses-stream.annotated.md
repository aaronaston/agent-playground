# Annotated: one streaming OpenAI Responses API call (2026-10-18)

Raw capture: [`openai-responses-stream.txt`](openai-responses-stream.txt), produced by
`experiments/capture_messages_stream.sh` (`curl -N -i`, model `gpt-4.1-mini`, prompt
"Count to five, one number per line, nothing else."). Session cookie and account ids
redacted.

## Headers

| Header | What it tells you |
|---|---|
| `HTTP/2 200` | ALPN picked HTTP/2; the stream is one h2 stream, not a dedicated connection. |
| `content-type: text/event-stream; charset=utf-8` | Same SSE content type as `sse_server.py`. |
| `server: cloudflare`, `cf-ray`, `cf-cache-status: DYNAMIC` | An L7 proxy (Cloudflare) terminates the connection; `DYNAMIC` means it did not try to cache the stream. |
| `openai-processing-ms: 1464` | Server-side time before the first byte, as the origin saw it. |
| `x-ratelimit-*` | Rate limits ride on response headers, the normal HTTP place for them. |
| `alt-svc: h3=":443"` | The server advertises HTTP/3 for next time; this is how h3 is discovered (not ALPN). |
| no `transfer-encoding: chunked` | HTTP/2 frames the body itself; chunked encoding is an HTTP/1.1 thing. |

## Event sequence

```
response.created              full response object, status in_progress, output []
response.in_progress          the same object again
response.output_item.added    an output item of type "message" begins (output_index 0)
response.content_part.added   a content part of type "output_text" begins inside it, text ""
response.output_text.delta    x9  "1", "  \n", "2", "  \n", "3", "  \n", "4", "  \n", "5"
response.output_text.done     the assembled text for that part
response.content_part.done    the finished part
response.output_item.done     the finished message item
response.completed            full response object again, now status completed and with usage
```

Shape: a fixed opening, a run of deltas, and a fixed closing that repeats the final
state at each level of nesting (part, item, response). A client that only wants the text
listens to `output_text.delta`; a client that wants the final object can ignore the
deltas and take `response.completed`.

## Things to notice

- **The SSE `event:` field carries the type**, and the JSON repeats it in `"type"`. This
  is the richest use of the event field in the study. MCP leaves it as `message`; the
  Anthropic Messages API uses it the same way as here (`message_start`,
  `content_block_delta`, ...).
- **No `id:` lines, so no `Last-Event-ID` resume.** Instead every event carries a
  `sequence_number`. Ordering is in the payload, not the SSE layer, and a dropped
  connection means starting over (or, for long jobs, `background: true` plus polling).
- **`obfuscation`**: random padding on every delta so that the encrypted size of each
  event does not reveal token lengths to someone watching the TLS stream. A side-channel
  fix visible on the wire.
- **The whole response object is sent three times** (created, in_progress, completed).
  Verbose, but it means a client that joins late or ignores deltas is never missing the
  envelope.
- **Usage arrives only at the end**, in `response.completed`: 19 input, 10 output, 29
  total. Nothing earlier can tell you the cost.
- **Timing**: first byte at 2.37 s, total 2.53 s. Almost all of the wait is before the
  stream starts; the stream itself took 0.16 s. For a short answer, streaming buys
  perceived latency on the first token, not throughput.
- **Each delta is tiny** (one token: a digit or `"  \n"`), so the per-event overhead
  (the ids and padding) is many times the payload. Fine over one HTTP/2 stream.

## Compared with `sse_server.py`

Same wire format, same content type, same blank-line framing. Differences: no `id:` or
`retry:`, so the browser-native resume story is not used; the event names are a
hierarchy that mirrors the response object; and the stream is one h2 stream behind a
CDN rather than a dedicated HTTP/1.1 connection to a Python process.
