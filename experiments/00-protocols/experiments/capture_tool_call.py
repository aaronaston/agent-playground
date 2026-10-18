#!/usr/bin/env python3
"""Capture a streamed LLM call that ends in a tool call, then the follow-up.

Two raw HTTP exchanges against the OpenAI Responses API, saved verbatim:

  1. POST with a `get_weather` tool defined. The stream ends with a
     function_call item instead of text: the model is asking the client to do
     something before it can finish.
  2. POST again with the whole conversation plus the tool's result as a
     function_call_output item. Stateless form (no previous_response_id), so
     the parallel with MCP's MRTR retry is exact.

Reads OPENAI_API_KEY from the environment or experiments/.env.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
ENV = HERE.parent.parent / ".env"
if not os.environ.get("OPENAI_API_KEY") and ENV.exists():
    for line in ENV.read_text().splitlines():
        if line.startswith("OPENAI_API_KEY="):
            os.environ["OPENAI_API_KEY"] = line.split("=", 1)[1].strip()
KEY = os.environ.get("OPENAI_API_KEY") or sys.exit("set OPENAI_API_KEY or put it in experiments/.env")

MODEL = sys.argv[1] if len(sys.argv) > 1 else "gpt-4.1-mini"
OUT = HERE / "captures" / "openai-tool-call-stream.txt"
TOOL = {
    "type": "function",
    "name": "get_weather",
    "description": "Current weather for a city.",
    "parameters": {"type": "object", "properties": {"city": {"type": "string"}},
                   "required": ["city"], "additionalProperties": False},
    "strict": True,
}
USER = {"role": "user", "content": "What's the weather in Toronto right now? One sentence."}


def post(body):
    cmd = ["curl", "-sS", "-N", "-i", "https://api.openai.com/v1/responses",
           "-H", f"Authorization: Bearer {KEY}", "-H", "content-type: application/json",
           "-d", json.dumps(body),
           "-w", "\n# curl: http %{http_version}, status %{http_code}, first byte %{time_starttransfer}s, total %{time_total}s\n"]
    raw = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    raw = re.sub(r"^set-cookie: .*$", "set-cookie: <redacted>", raw, flags=re.M)
    raw = re.sub(r"^(openai-organization|openai-project): .*$", r"\1: <redacted>", raw, flags=re.M)
    return raw


def events(raw):
    return [json.loads(l[6:]) for l in raw.splitlines() if l.startswith("data: ")]


# ---- exchange 1: the model decides it needs a tool -------------------------
req1 = {"model": MODEL, "stream": True, "tools": [TOOL], "input": [USER]}
raw1 = post(req1)
done = [e for e in events(raw1) if e["type"] == "response.completed"][0]
calls = [i for i in done["response"]["output"] if i["type"] == "function_call"]
if not calls:
    sys.exit("model did not call the tool; raw response:\n" + raw1)
call = calls[0]
args = json.loads(call["arguments"])
print(f"exchange 1: model asked for {call['name']}({args}) call_id={call['call_id']}")

# ---- the client runs the tool -----------------------------------------------
tool_result = {"city": args.get("city"), "temp_c": 11, "conditions": "overcast, light wind"}

# ---- exchange 2: same conversation, plus the call and its output ------------
req2 = {"model": MODEL, "stream": True, "tools": [TOOL],
        "input": [USER,
                  {"type": "function_call", "call_id": call["call_id"], "name": call["name"], "arguments": call["arguments"]},
                  {"type": "function_call_output", "call_id": call["call_id"], "output": json.dumps(tool_result)}]}
raw2 = post(req2)
final = [e for e in events(raw2) if e["type"] == "response.completed"][0]
text = "".join(c["text"] for i in final["response"]["output"] if i["type"] == "message" for c in i["content"] if c["type"] == "output_text")
print(f"exchange 2: model answered: {text!r}")

sep = "=" * 78
OUT.write_text(
    f"{sep}\n# EXCHANGE 1  request body\n{sep}\n{json.dumps(req1, indent=1)}\n\n"
    f"{sep}\n# EXCHANGE 1  response (stream ends with a function_call)\n{sep}\n{raw1}\n"
    f"{sep}\n# CLIENT runs the tool locally -> {json.dumps(tool_result)}\n{sep}\n\n"
    f"{sep}\n# EXCHANGE 2  request body (whole conversation + call + output)\n{sep}\n{json.dumps(req2, indent=1)}\n\n"
    f"{sep}\n# EXCHANGE 2  response (stream ends with text)\n{sep}\n{raw2}\n")
print(f"saved {OUT}")
for n, raw in ((1, raw1), (2, raw2)):
    print(f"\nexchange {n} event types, in order:")
    last, count = None, 0
    for e in events(raw) + [{"type": None}]:
        if e["type"] == last:
            count += 1; continue
        if last:
            print(f"  {last:<45} x{count}")
        last, count = e["type"], 1
