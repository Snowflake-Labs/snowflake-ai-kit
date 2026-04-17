#!/bin/bash
# Uninstallation script for cortexcode-tool

set -e

echo "==> Uninstalling cortexcode-tool..."

INSTALL_DIR="$HOME/.local/lib/cortexcode-tool"
BIN_FILE="$HOME/.local/bin/cortexcode-tool"
CONFIG_DIR="$HOME/.config/cortexcode-tool"
CACHE_DIR="$HOME/.cache/cortexcode-tool"

# Remove binary and library
if [ -f "$BIN_FILE" ]; then
    echo "Removing binary: $BIN_FILE"
    rm "$BIN_FILE"
fi

if [ -d "$INSTALL_DIR" ]; then
    echo "Removing library: $INSTALL_DIR"
    rm -rf "$INSTALL_DIR"
fi

# Ask about config
if [ -d "$CONFIG_DIR" ]; then
    read -p "Remove configuration? ($CONFIG_DIR) [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$CONFIG_DIR"
        echo "Removed configuration"
    else
        echo "Kept configuration"
    fi
fi

# Ask about cache
if [ -d "$CACHE_DIR" ]; then
    read -p "Remove cache? ($CACHE_DIR) [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$CACHE_DIR"
        echo "Removed cache"
    else
        echo "Kept cache"
    fi
fi

# Ask about audit logs
AUDIT_LOG="$HOME/.config/cortexcode-tool/audit.log"
if [ -f "$AUDIT_LOG" ]; then
    read -p "Remove audit logs? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm "$AUDIT_LOG"*
        echo "Removed audit logs"
    else
        echo "Kept audit logs"
    fi
fi

echo ""
echo "==> Uninstallation complete"
echo ""
echo "Removed:"
echo "  - Binary: $BIN_FILE"
echo "  - Library: $INSTALL_DIR"
echo ""
