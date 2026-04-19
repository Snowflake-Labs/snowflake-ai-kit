#!/bin/bash
set -e

echo "==> Uninstalling cortexcode-tool (Codex integration)..."
echo ""

# The Codex integration uses cortexcode-tool under the hood.
# Delegate to the cli-tool uninstaller.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

if [ -f "$REPO_ROOT/integrations/cli-tool/uninstall.sh" ]; then
    bash "$REPO_ROOT/integrations/cli-tool/uninstall.sh"
else
    echo "cli-tool uninstaller not found. Removing manually..."
    rm -f "$HOME/.local/bin/cortexcode-tool"
    rm -rf "$HOME/.local/lib/cortexcode-tool"
    echo "Removed cortexcode-tool binary and library."
    echo "Config at ~/.config/cortexcode-tool/ and cache at ~/.cache/cortexcode-tool/ preserved."
fi

echo ""
echo "==> Codex integration uninstalled"
