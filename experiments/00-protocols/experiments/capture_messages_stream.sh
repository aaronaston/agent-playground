#!/usr/bin/env bash
# Step 1.5: capture one streaming LLM response, raw, as the bytes arrive.
# Uses the OpenAI Responses API. Reads OPENAI_API_KEY from the environment or
# from experiments/.env (shared by all experiments).
set -euo pipefail
cd "$(dirname "$0")"
[ -z "${OPENAI_API_KEY:-}" ] && [ -f ../../.env ] && set -a && . ../../.env && set +a
: "${OPENAI_API_KEY:?set OPENAI_API_KEY or put it in experiments/.env}"

OUT=captures/openai-responses-stream.txt
MODEL=${1:-gpt-4.1-mini}

# -N: no output buffering, so events print as they arrive.
# -i: include the response headers in the capture; they are part of the lesson.
# -w: append timing after the body.
curl -sS -N -i https://api.openai.com/v1/responses \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "content-type: application/json" \
  -d "{\"model\":\"$MODEL\",\"stream\":true,\"max_output_tokens\":60,
       \"input\":\"Count to five, one number per line, nothing else.\"}" \
  -w '\n\n# curl: http %{http_version}, status %{http_code}, first byte %{time_starttransfer}s, total %{time_total}s\n' \
  | tee "$OUT"

echo
echo "saved to $OUT"
echo "event types seen, in order:"
grep -E '^event:' "$OUT" | awk '{print $2}' | uniq -c | awk '{printf "  %-40s x%s\n", $2, $1}'
