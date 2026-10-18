#!/usr/bin/env bash
# Step 1.6: drive server.py with curl and save every byte, both protocol families.
# Start the server first: uv run python server.py
set -euo pipefail
cd "$(dirname "$0")"
U=http://127.0.0.1:8000/mcp
OUT=captures/streamable-http-session.txt
sep() { printf '\n%s\n# %s\n%s\n' "$(printf '=%.0s' {1..78})" "$1" "$(printf '=%.0s' {1..78})"; }
post() { # $1 label, $2 body, rest: extra headers
  local label=$1 body=$2; shift 2
  sep "$label"
  echo "# request body: $body"; echo
  curl -sS -N -i --max-time 20 "$U" -H 'content-type: application/json' \
       -H 'accept: application/json, text/event-stream' "${@/#/-H}" -d "$body" \
       -w '\n# curl: http %{http_version}, status %{http_code}, first byte %{time_starttransfer}s, total %{time_total}s\n' || true
}
{
META='"_meta":{"io.modelcontextprotocol/protocolVersion":"2026-07-28","io.modelcontextprotocol/clientInfo":{"name":"curl-study","version":"0"},"io.modelcontextprotocol/clientCapabilities":{},"io.modelcontextprotocol/logLevel":"info"'
sep "PART A: 2026-07-28 (modern, stateless). No initialize; version and capabilities in _meta on every request."
post "A1 tools/list" "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/list\",\"params\":{$META}}}" \
     "MCP-Protocol-Version: 2026-07-28" "Mcp-Method: tools/list"
post "A2 tools/call slow_count(2) with a progressToken" "{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/call\",\"params\":{\"name\":\"slow_count\",\"arguments\":{\"n\":2},$META,\"progressToken\":\"p1\"}}}" \
     "MCP-Protocol-Version: 2026-07-28" "Mcp-Method: tools/call" "Mcp-Name: slow_count"
post "A3 same call WITHOUT the Mcp-Method header (what does the server do?)" "{\"jsonrpc\":\"2.0\",\"id\":3,\"method\":\"tools/list\",\"params\":{$META}}}" \
     "MCP-Protocol-Version: 2026-07-28"

sep "PART B: 2025-06-18 (handshake family). initialize first; session id in a header."
INIT='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"curl-study","version":"0"}}}'
sep "B1 initialize"; echo "# request body: $INIT"; echo
HDRS=$(mktemp)
curl -sS -N -i --max-time 20 "$U" -H 'content-type: application/json' -H 'accept: application/json, text/event-stream' \
     -d "$INIT" -D "$HDRS" -w '\n# curl: status %{http_code}\n' || true
SID=$(grep -i '^mcp-session-id:' "$HDRS" | awk '{print $2}' | tr -d '\r')
echo "# session id minted by server: ${SID:-<none>}"
post "B2 notifications/initialized" '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
     "MCP-Protocol-Version: 2025-06-18" "Mcp-Session-Id: $SID"
post "B3 tools/call slow_count(2), session header, progressToken" '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"slow_count","arguments":{"n":2},"_meta":{"progressToken":"p1"}}}' \
     "MCP-Protocol-Version: 2025-06-18" "Mcp-Session-Id: $SID"
post "B4 tools/call WITHOUT the session header" '{"jsonrpc":"2.0","id":3,"method":"tools/list","params":{}}' \
     "MCP-Protocol-Version: 2025-06-18"
sep "B5 GET (2025 standalone stream) and DELETE (end session)"
curl -sS -i --max-time 5 "$U" -H 'accept: text/event-stream' -H "Mcp-Session-Id: $SID" -H "MCP-Protocol-Version: 2025-06-18" -w '\n# curl: status %{http_code}\n' || true
curl -sS -i -X DELETE "$U" -H "Mcp-Session-Id: $SID" -H "MCP-Protocol-Version: 2025-06-18" -w '\n# curl: status %{http_code}\n' || true
rm -f "$HDRS"
} 2>&1 | tee "$OUT"
echo; echo "saved $OUT"
