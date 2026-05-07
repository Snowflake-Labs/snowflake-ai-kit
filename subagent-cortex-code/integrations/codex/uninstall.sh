#!/bin/bash
set -e

INSTALL_LIB_DIR="$HOME/.local/lib/cortexcode-tool"
BIN_PATH="$HOME/.local/bin/cortexcode-tool"
CONFIG_PATH="$INSTALL_LIB_DIR/config.yaml"
CACHE_DIR="$HOME/.cache/cortexcode-tool"

# Historical Codex skill install path from early prototypes.
LEGACY_SKILL_DIR="$HOME/.codex/skills/cortex-code"

echo "Uninstalling Codex cortexcode-tool integration"

if [ -f "$CONFIG_PATH" ]; then
    BACKUP="$CONFIG_PATH.backup.$(date +%Y%m%d_%H%M%S)"
    echo "Backing up config to $BACKUP"
    cp "$CONFIG_PATH" "$BACKUP"
fi

if [ -f "$CACHE_DIR/audit.log" ]; then
    BACKUP="$CACHE_DIR/audit.log.backup.$(date +%Y%m%d_%H%M%S)"
    echo "Backing up audit log to $BACKUP"
    cp "$CACHE_DIR/audit.log" "$BACKUP"
fi

if [ -f "$BIN_PATH" ]; then
    rm -f "$BIN_PATH"
    echo "✓ Removed $BIN_PATH"
else
    echo "No cortexcode-tool binary found at $BIN_PATH"
fi

if [ -d "$INSTALL_LIB_DIR" ]; then
    find "$INSTALL_LIB_DIR" -type f ! -name "*.backup.*" -delete
    find "$INSTALL_LIB_DIR" -type d -empty -delete
    echo "✓ Removed installed package files from $INSTALL_LIB_DIR"
else
    echo "No installed package found at $INSTALL_LIB_DIR"
fi

if [ -d "$LEGACY_SKILL_DIR" ]; then
    echo "Legacy Codex skill directory still exists: $LEGACY_SKILL_DIR"
    echo "Remove it manually if you no longer need it."
fi

if [ -d "$CACHE_DIR" ]; then
    echo "Audit/log cache preserved at $CACHE_DIR"
fi
