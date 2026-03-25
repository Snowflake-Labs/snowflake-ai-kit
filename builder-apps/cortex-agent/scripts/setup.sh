#!/usr/bin/env bash
# Cortex Agent App — Setup Script
# Run from the builder-apps/cortex-agent/ directory.

set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== Cortex Agent App Setup ==="
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
  echo "WARNING: No Snowflake connection configured."
  echo "  Set one up (shared by both snow and cortex CLIs):"
  echo "    snow connection add"
  echo "  This creates ~/.snowflake/connections.toml, used by both tools."
  echo "  Or configure .env.local after setup."
fi
echo ""

# Create .env.local if it doesn't exist
if [ ! -f .env.local ]; then
  cp .env.example .env.local
  echo "Created .env.local from .env.example"
  echo ">>> Edit .env.local with your Snowflake credentials <<<"
  echo ""
else
  echo ".env.local already exists, skipping"
fi

# Install Python dependencies
echo "Installing Python dependencies..."
if command -v uv &>/dev/null; then
  uv pip install -r requirements.txt
else
  pip install -r requirements.txt
fi
echo ""

# Install Node dependencies
echo "Installing Node dependencies..."
cd client
npm install
cd ..
echo ""

echo ""
echo "=== Setup complete ==="
echo ""
echo "Before starting:"
echo "  1. Run setup.sql in a Snowflake worksheet to create sample data + agent"
echo "  2. Edit .env.local with your Snowflake credentials"
echo ""
echo "To start the app:"
echo "  ./scripts/dev.sh"
