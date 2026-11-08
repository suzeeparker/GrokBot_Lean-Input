#!/usr/bin/env bash
# startServers.sh — sync config, then start/restart census API + MCP servers

NODE="/c/Users/Robin/AppData/Local/nvs/default/x64/node.exe"
SCRIPTS="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPTS/../.." && pwd)"
API_DIR="$ROOT/server/s02_census-data-api"
MCP_DIR="$ROOT/server/s02_census-data-mcp"
API_PORT=3252
API_LOG="$API_DIR/api.log"
MCP_LOG="$MCP_DIR/mcp.log"

# --- 1. Copy prompts ---
echo "==> Copying prompts"
bash "$SCRIPTS/copyPrompts.sh"

# --- 2. Copy mcp.json to global Amazon Q config ---
echo "==> Copying mcp.json"
 MCP_SRC="$ROOT/.amazonq/mcp.json"
 MCP_DEST="$HOME/.aws/amazonq/default.json"
#MCP_DEST="$ROOT/.amazonq/default.json"

cp "$MCP_SRC" "$MCP_DEST"
echo "  Copied mcp.json to $MCP_DEST"

# --- helpers ---
kill_port() {
  local pid
  pid=$(netstat -ano 2>/dev/null | grep ":$1 " | grep LISTENING | awk '{print $5}' | head -1)
  if [ -n "$pid" ]; then
    echo "  Stopping PID $pid on port $1..."
    taskkill //PID "$pid" //F > /dev/null 2>&1
    sleep 1
  fi
}

wait_for_port() {
  local port=$1 retries=10
  while [ $retries -gt 0 ]; do
    if curl -s "http://localhost:$port/api/health" > /dev/null 2>&1; then
      return 0
    fi
    sleep 0.5
    ((retries--))
  done
  return 1
}

# --- 3. Start API server ---
echo "==> Census API (port $API_PORT)"
kill_port $API_PORT
cd "$API_DIR"
"$NODE" server.mjs > "$API_LOG" 2>&1 &
echo "  Started (PID $!), waiting for health check..."
if wait_for_port $API_PORT; then
  echo "  OK — http://localhost:$API_PORT/api/health"
else
  echo "  ERROR — API did not start. Check $API_LOG"
  exit 1
fi

# --- 4. Start MCP server ---
echo "==> Census MCP server"
pkill -f "mcp-census.mjs" 2>/dev/null && sleep 1
cd "$MCP_DIR"
"$NODE" mcp-census.mjs > "$MCP_LOG" 2>&1 &
echo "  Started (PID $!)"
echo "  Log: $MCP_LOG"

echo ""
echo "Done."
