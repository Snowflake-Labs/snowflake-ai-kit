#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
# Config goes next to the installed package so cortexcode-tool finds it
# without needing a --config flag (checked before ~/.config/ fallback).
INSTALL_LIB_DIR="$HOME/.local/lib/cortexcode-tool"

echo "==> Installing cortexcode-tool for Codex..."
echo ""

# ── Step 1: Ensure cortexcode-tool is installed ────────────────────────────
if ! command -v cortexcode-tool &>/dev/null; then
    echo "cortexcode-tool not found. Installing now..."
    echo ""
    bash "$REPO_ROOT/integrations/cli-tool/setup.sh"
    echo ""

    if ! command -v cortexcode-tool &>/dev/null; then
        echo "Error: cortexcode-tool install failed. Please install manually:"
        echo "  bash $REPO_ROOT/integrations/cli-tool/setup.sh"
        exit 1
    fi
else
    echo "✓ cortexcode-tool already installed: $(which cortexcode-tool)"
    if ! cortexcode-tool --version &>/dev/null; then
        echo "Existing cortexcode-tool failed verification. Reinstalling..."
        bash "$REPO_ROOT/integrations/cli-tool/setup.sh"
        echo ""
    fi
fi

# ── Step 2: Auto-detect active Cortex connection ───────────────────────────
echo ""
echo "Detecting active Cortex connection..."
ACTIVE_CONNECTION=""
if command -v cortex &>/dev/null; then
    ACTIVE_CONNECTION=$(cortex connections list 2>/dev/null \
        | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('active_connection',''))" \
        2>/dev/null || true)
fi

if [ -n "$ACTIVE_CONNECTION" ]; then
    echo "✓ Active connection: $ACTIVE_CONNECTION"
else
    echo "  Warning: Could not detect active connection. Using 'default'."
    echo "  Run 'cortex connections list' to check, then edit $INSTALL_LIB_DIR/config.yaml"
    ACTIVE_CONNECTION="default"
fi

# ── Step 3: Write config next to the installed package ───────────────────
echo ""
echo "Writing config to $INSTALL_LIB_DIR/config.yaml..."
mkdir -p "$INSTALL_LIB_DIR"
chmod 700 "$INSTALL_LIB_DIR"
sed "s/connection_name: \"default\"/connection_name: \"$ACTIVE_CONNECTION\"/" \
    "$SCRIPT_DIR/cortexcode-tool-codex.yaml" > "$INSTALL_LIB_DIR/config.yaml"
chmod 600 "$INSTALL_LIB_DIR/config.yaml"

# ── Step 4: Summary ────────────────────────────────────────────────────────
echo ""
echo "✓ Installation complete"
echo ""
echo "  CLI tool   : $(which cortexcode-tool)"
echo "  Config     : $INSTALL_LIB_DIR/config.yaml  (auto-detected, no --config flag needed)"
echo "  Connection : $ACTIVE_CONNECTION"
echo ""
echo "Usage from Codex:"
echo "  cortexcode-tool --yes \"your question\" --envelope RO"
echo "  (Use --yes only after Codex chat approval.)"
echo ""
echo "Verify:"
echo "  cortexcode-tool --version"
echo "  cortexcode-tool --yes \"How many databases do I have in Snowflake?\" --envelope RO"
