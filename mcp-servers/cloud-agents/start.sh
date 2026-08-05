#!/bin/bash
# Cloud Agents MCP server launcher.
#
# Auth (in priority order):
#   1. CLOUD_AGENTS_SESSION_TOKEN env var (if set)
#   2. PAT_SNOWHOUSE / CLOUD_AGENTS_PAT / SNOWFLAKE_PAT
#   3. Token file from token_provider.py (/tmp/cloud-agents-token.txt)
#   4. Starts token_provider.py automatically (triggers browser SSO once)
#
# Usage:
#   ./start.sh   # auto-starts token provider if needed

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
export CLOUD_AGENTS_HOST="${CLOUD_AGENTS_HOST:-https://snowhouse.snowflakecomputing.com}"
TOKEN_FILE="${CLOUD_AGENTS_TOKEN_FILE:-/tmp/cloud-agents-token.txt}"

# If no auth available, try token file or start provider
if [ -z "$CLOUD_AGENTS_SESSION_TOKEN" ] && [ -z "$PAT_SNOWHOUSE" ] && [ -z "$CLOUD_AGENTS_PAT" ] && [ -z "$SNOWFLAKE_PAT" ]; then
  if [ -f "$TOKEN_FILE" ]; then
    export CLOUD_AGENTS_SESSION_TOKEN=$(cat "$TOKEN_FILE")
  else
    echo "Starting token provider (browser SSO will open)..." >&2
    python3 "$SCRIPT_DIR/token_provider.py" &
    PROVIDER_PID=$!
    # Wait for token file to appear (up to 30s)
    for i in $(seq 1 30); do
      if [ -f "$TOKEN_FILE" ]; then break; fi
      sleep 1
    done
    if [ ! -f "$TOKEN_FILE" ]; then
      echo "ERROR: Token provider failed to start." >&2
      kill $PROVIDER_PID 2>/dev/null
      exit 1
    fi
    export CLOUD_AGENTS_SESSION_TOKEN=$(cat "$TOKEN_FILE")
    trap "kill $PROVIDER_PID 2>/dev/null" EXIT
  fi
fi

exec node "$SCRIPT_DIR/src/server.mjs"
