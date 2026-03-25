#!/usr/bin/env bash
# Snowflake Builder App — Setup Script
# Run from the builder-apps/claude-agent/ directory.

set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== Snowflake Builder App Setup ==="
echo ""

# Check prerequisites
check_cmd() {
  if ! command -v "$1" &>/dev/null; then
    echo "ERROR: $1 is required but not installed."
    exit 1
  fi
}

check_cmd python3
check_cmd node
check_cmd npm

echo "Prerequisites OK (python3, node, npm)"

# Check Snowflake auth
if [ -f "$HOME/.snowflake/connections.toml" ]; then
  echo "Snowflake config found (~/.snowflake/connections.toml)"
elif [ -n "${SNOWFLAKE_HOST:-}" ] || [ -n "${SNOWFLAKE_ACCOUNT:-}" ]; then
  echo "Snowflake config found (environment variables)"
else
  echo ""
  echo "WARNING: No Snowflake config detected."
  echo "  You'll need one of:"
  echo "    - ~/.snowflake/connections.toml (recommended)"
  echo "    - SNOWFLAKE_HOST + SNOWFLAKE_ACCOUNT + SNOWFLAKE_PAT env vars"
  echo "  Or configure .env.local after setup."
fi

# Check Anthropic API key
if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
  echo ""
  echo "NOTE: ANTHROPIC_API_KEY not set. You'll need to add it to .env.local."
fi
echo ""

# Create .env.local if it doesn't exist
if [ ! -f .env.local ]; then
  cp .env.example .env.local
  echo "Created .env.local from .env.example"
  echo ">>> Edit .env.local with your Snowflake and Anthropic credentials <<<"
  echo ""
else
  echo ".env.local already exists, skipping"
fi

# Install Python dependencies
echo "Installing Python dependencies..."
if command -v uv &>/dev/null; then
  uv pip install -r requirements.txt
  uv pip install -e packages/snowflake-tools-core -e packages/snowflake-mcp-server
else
  pip install -r requirements.txt
  pip install -e packages/snowflake-tools-core -e packages/snowflake-mcp-server
fi
echo ""

# Install Node dependencies
echo "Installing Node dependencies..."
cd client
npm install
cd ..
echo ""

# Create projects directory
mkdir -p projects

echo ""
echo "=== Setup complete ==="
echo ""
echo "To start the app:"
echo "  ./scripts/dev.sh"
echo ""
echo "Or start manually:"
echo "  # Terminal 1 — Backend"
echo "  uvicorn server.main:app --reload --port 8000"
echo ""
echo "  # Terminal 2 — Frontend"
echo "  cd client && npm run dev"
