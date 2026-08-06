#!/bin/bash
set -e

# Cloud Agents MCP — One-command test setup
# Usage: ./test-setup.sh [--teardown]

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TOKEN_FILE="/tmp/cloud-agents-token.txt"
CLAUDE_JSON="$HOME/.claude.json"
MCP_START="$SCRIPT_DIR/start.sh"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}✓${NC} $1"; }
warn()  { echo -e "${YELLOW}!${NC} $1"; }
fail()  { echo -e "${RED}✗${NC} $1"; exit 1; }

# ── Teardown mode ──────────────────────────────────────────────────
if [ "$1" = "--teardown" ]; then
  echo "Cleaning up Cloud Agents MCP test setup..."
  
  # Stop token provider
  pkill -f "token_provider.py" 2>/dev/null && info "Stopped token provider" || warn "Token provider not running"
  
  # Remove token file
  rm -f "$TOKEN_FILE" && info "Removed $TOKEN_FILE"
  
  # Remove cloud-agents from ~/.claude.json
  if [ -f "$CLAUDE_JSON" ]; then
    python3 -c "
import json, sys
with open('$CLAUDE_JSON', 'r') as f:
    config = json.load(f)
if 'mcpServers' in config and 'cloud-agents' in config['mcpServers']:
    del config['mcpServers']['cloud-agents']
    if not config['mcpServers']:
        del config['mcpServers']
    with open('$CLAUDE_JSON', 'w') as f:
        json.dump(config, f, indent=2)
        f.write('\n')
    print('Removed cloud-agents from ~/.claude.json')
else:
    print('cloud-agents not in ~/.claude.json (already clean)')
" && info "Updated ~/.claude.json"
  fi
  
  # Remove user-level hook
  HOOKS_FILE="$HOME/.claude/hooks.json"
  if [ -f "$HOOKS_FILE" ]; then
    python3 -c "
import json, os
hooks_file = os.path.expanduser('~/.claude/hooks.json')
with open(hooks_file, 'r') as f:
    config = json.load(f)
if 'hooks' in config and 'UserPromptSubmit' in config['hooks']:
    del config['hooks']['UserPromptSubmit']
    if not config['hooks']:
        del config['hooks']
    with open(hooks_file, 'w') as f:
        json.dump(config, f, indent=2)
        f.write('\n')
" && info "Removed user-level hook from ~/.claude/hooks.json"
  fi
  
  # Re-enable marketplace plugin
  claude plugin enable snowflake-cortex-code@claude-plugins-official 2>/dev/null && info "Re-enabled marketplace plugin" || warn "Marketplace plugin not found"
  
  echo ""
  info "Teardown complete. Normal Cortex Code plugin routing restored."
  exit 0
fi

# ── Setup mode ─────────────────────────────────────────────────────
echo "═══════════════════════════════════════════════════════"
echo " Cloud Agents MCP — Test Setup"
echo "═══════════════════════════════════════════════════════"
echo ""

# Check prerequisites
echo "Checking prerequisites..."
command -v node >/dev/null 2>&1 || fail "Node.js not found. Install Node 20+."
NODE_VERSION=$(node --version | sed 's/v//' | cut -d. -f1)
[ "$NODE_VERSION" -ge 20 ] || fail "Node.js 20+ required (found v$NODE_VERSION)"
info "Node.js $(node --version)"

command -v python3 >/dev/null 2>&1 || fail "Python 3 not found."
python3 -c "import snowflake.connector" 2>/dev/null || fail "snowflake-connector-python not installed. Run: pip3 install snowflake-connector-python"
info "Python 3 + snowflake-connector-python"

command -v claude >/dev/null 2>&1 || fail "Claude Code CLI not found."
info "Claude Code CLI $(claude --version 2>/dev/null | head -1)"

# Run unit tests
echo ""
echo "Running unit tests..."
cd "$SCRIPT_DIR"
node --test tests/*.test.mjs >/dev/null 2>&1 && info "23/23 unit tests pass" || fail "Unit tests failed"

# Start token provider (if not already running)
echo ""
echo "Starting Snowhouse token provider..."
if [ -f "$TOKEN_FILE" ] && pgrep -f "token_provider.py" >/dev/null 2>&1; then
  info "Token provider already running"
else
  # Get username for Snowhouse auth
  if [ -z "$CLOUD_AGENTS_USER" ]; then
    printf "  Snowhouse username: "
    read -r CLOUD_AGENTS_USER
    [ -n "$CLOUD_AGENTS_USER" ] || fail "Username is required."
  fi
  export CLOUD_AGENTS_USER

  pkill -f "token_provider.py" 2>/dev/null || true
  rm -f "$TOKEN_FILE"
  python3 "$SCRIPT_DIR/token_provider.py" &
  PROVIDER_PID=$!
  
  # Wait for token (browser SSO will open)
  echo "  Waiting for browser SSO login..."
  for i in $(seq 1 45); do
    if [ -f "$TOKEN_FILE" ]; then break; fi
    sleep 1
  done
  
  if [ ! -f "$TOKEN_FILE" ]; then
    kill $PROVIDER_PID 2>/dev/null
    fail "Token provider failed to start (timeout). Check browser for SSO prompt."
  fi
  info "Token provider running (PID $PROVIDER_PID)"
fi

# Configure MCP server in ~/.claude.json
echo ""
echo "Configuring MCP server..."
python3 -c "
import json, os

claude_json = os.path.expanduser('~/.claude.json')
config = {}
if os.path.exists(claude_json):
    with open(claude_json, 'r') as f:
        config = json.load(f)

config.setdefault('mcpServers', {})
config['mcpServers']['cloud-agents'] = {
    'type': 'stdio',
    'command': '$MCP_START',
    'args': [],
    'env': {
        'CLOUD_AGENTS_HOST': 'https://snowhouse.snowflakecomputing.com',
        'CLOUD_AGENTS_TOKEN_FILE': '$TOKEN_FILE',
        'CLOUD_AGENTS_MCP_STATE_DIR': os.path.expanduser('~/.snowflake/cloud-agents-mcp')
    }
}

with open(claude_json, 'w') as f:
    json.dump(config, f, indent=2)
    f.write('\n')
"
info "Added cloud-agents to ~/.claude.json"

# Install user-level hook for auto-routing (works from any directory)
echo ""
echo "Installing user-level hook..."
HOOKS_FILE="$HOME/.claude/hooks.json"
mkdir -p "$HOME/.claude"
python3 -c "
import json, os

hooks_file = os.path.expanduser('~/.claude/hooks.json')
config = {}
if os.path.exists(hooks_file):
    with open(hooks_file, 'r') as f:
        config = json.load(f)

config.setdefault('hooks', {})
config['hooks']['UserPromptSubmit'] = [
    {
        'type': 'command',
        'command': 'python3 $SCRIPT_DIR/../../../plugins/cortex-code/scripts/router/prompt_filter.py'
    }
]

with open(hooks_file, 'w') as f:
    json.dump(config, f, indent=2)
    f.write('\n')
"
info "Installed hook in ~/.claude/hooks.json (auto-routes Snowflake prompts)"

# Disable marketplace plugin (if installed — avoids duplicate hooks)
echo ""
echo "Configuring Claude Code..."
claude plugin disable snowflake-cortex-code@claude-plugins-official 2>/dev/null && info "Disabled marketplace plugin (avoids duplicate hooks)" || info "Marketplace plugin not installed (OK — hook handles routing)"

# Verify MCP server responds
echo ""
echo "Verifying MCP server..."
RESPONSE=$(echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05"}}' | "$MCP_START" 2>/dev/null)
if echo "$RESPONSE" | grep -q "cloud-agents-mcp"; then
  info "MCP server responds correctly"
else
  fail "MCP server did not respond. Check token provider."
fi

# Done
echo ""
echo "═══════════════════════════════════════════════════════"
echo -e " ${GREEN}Setup complete!${NC}"
echo "═══════════════════════════════════════════════════════"
echo ""
echo " Open a new terminal from the repo directory and run:"
echo ""
echo "   cd $REPO_ROOT"
echo "   sf ai claude    # internal Snowflake users"
echo "   # or"
echo "   claude          # external users"
echo ""
echo " Then ask any Snowflake question:"
echo "   > show me my snowflake databases"
echo ""
echo " Approve MCP tool permission once when prompted."
echo ""
echo " When done:"
echo "   $SCRIPT_DIR/test-setup.sh --teardown"
echo ""
