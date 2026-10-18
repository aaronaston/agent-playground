#!/usr/bin/env bash
# Step 1.5: capture one streaming Messages API response, raw, as the bytes arrive.
# Reads ANTHROPIC_API_KEY from the environment or from ../.env next to this experiment.
set -euo pipefail
cd "$(dirname "$0")"
[ -z "${ANTHROPIC_API_KEY:-}" ] && [ -f ../.env ] && set -a && . ../.env && set +a
: "${ANTHROPIC_API_KEY:?set ANTHROPIC_API_KEY or put it in experiments/00-protocols/.env}"

OUT=captures/messages-stream.txt
MODEL=${1:-claude-opus-5-5}

# -N: no output buffering, so events print as they arrive.
# -i: include the response headers in the capture; they are part of the lesson.
# -w: append timing after the body.
curl -sS -N -i https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d "{\"model\":\"$MODEL\",\"max_tokens\":200,\"stream\":true,
       \"messages\":[{\"role\":\"user\",\"content\":\"Count to five, one number per line, nothing else.\"}]}" \
  -w '\n\n# curl: http %{http_version}, status %{http_code}, first byte %{time_starttransfer}s, total %{time_total}s\n' \
  | tee "$OUT"

echo
echo "saved to $OUT"
echo "event types seen, in order:"
grep -E '^event:' "$OUT" | awk '{print "  " $2}' | uniq -c | awk '{printf "  %s x%s\n", $2, $1}'
