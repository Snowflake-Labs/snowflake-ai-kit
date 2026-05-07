#!/bin/bash
set -e

TARGET=~/.claude/skills/cortex-code

echo "Uninstalling Claude Code skill from $TARGET"

# Backup config if exists
if [ -f "$TARGET/config.yaml" ]; then
    BACKUP="$TARGET/config.yaml.backup.$(date +%Y%m%d_%H%M%S)"
    echo "Backing up config to $BACKUP"
    cp "$TARGET/config.yaml" "$BACKUP"
fi

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
    echo "✓ Claude Code skill uninstalled successfully"
    echo "  Backups preserved at: $TARGET/*.backup.*"
else
    echo "Claude Code skill not found at $TARGET"
fi
