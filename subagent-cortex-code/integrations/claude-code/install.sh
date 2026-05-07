#!/bin/bash
set -e

TARGET=~/.claude/skills/cortex-code
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "Installing Claude Code skill to $TARGET"

# Create directories
mkdir -p "$TARGET/scripts" "$TARGET/security/policies"

# Copy shared components
echo "Copying shared scripts..."
cp -r "$REPO_ROOT/shared/scripts/"* "$TARGET/scripts/"
echo "Copying shared security modules..."
cp -r "$REPO_ROOT/shared/security/"* "$TARGET/security/"

# Parameterize for Claude (replace __CODING_AGENT__ with claude)
echo "Parameterizing for Claude..."
python3 - "$TARGET" <<'PY'
import sys
from pathlib import Path
root = Path(sys.argv[1])
for path in root.rglob("*.py"):
    path.write_text(path.read_text().replace("__CODING_AGENT__", "claude"))
PY

# Copy Claude Code specific files
echo "Copying Claude Code specific files..."
cp "$REPO_ROOT/integrations/claude-code/skill.md" "$TARGET/"
cp "$REPO_ROOT/integrations/claude-code/config.yaml.example" "$TARGET/"
cp "$REPO_ROOT/integrations/claude-code/config.yaml" "$TARGET/"

# Note: config.yaml defaults to approval_mode: "prompt" for interactive safety.
# Users can opt into auto/envelope_only modes via config.yaml.example if needed.

# Secure installed files
chmod 700 "$TARGET"
find "$TARGET" -type d -exec chmod 700 {} \;
find "$TARGET" -type f -exec chmod 600 {} \;
find "$TARGET/scripts" -name "*.py" -exec chmod 700 {} \;

echo ""
echo "✓ Claude Code skill installed successfully"
echo "  Location: $TARGET"
echo "  Config: $TARGET/config.yaml"
echo "  Audit log: ~/.claude/skills/cortex-code/audit.log"
echo ""
echo "Test with: /cortex-code How many databases do I have?"
