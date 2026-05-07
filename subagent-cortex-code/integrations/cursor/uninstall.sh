#!/bin/bash
set -e

TARGET=~/.cursor/skills/cortex-code

echo "Uninstalling Cursor skill from $TARGET"

# Backup audit log if exists
if [ -f "$TARGET/audit.log" ]; then
    BACKUP="$TARGET/audit.log.backup.$(date +%Y%m%d_%H%M%S)"
    echo "Backing up audit log to $BACKUP"
    cp "$TARGET/audit.log" "$BACKUP"
fi

# Remove the skill directory
if [ -d "$TARGET" ]; then
    # Keep backups, remove everything else
    find "$TARGET" -type f ! -name "*.backup.*" -delete
    find "$TARGET" -type d -empty -delete
    echo "✓ Cursor skill uninstalled successfully"
    echo "  Backups preserved at: $TARGET/*.backup.*"
else
    echo "Cursor skill not found at $TARGET"
fi
