#!/bin/bash
set -e

SKILL_TARGET="$HOME/.cursor/skills-cursor/cortex-code"
RULES_FILE="$HOME/.cursor/rules/cortex-snowflake-routing.mdc"

echo "==> Uninstalling Cortex Code skill from Cursor..."

# Backup audit log if exists
if [ -f "$SKILL_TARGET/audit.log" ]; then
    BACKUP="$SKILL_TARGET/audit.log.backup.$(date +%Y%m%d_%H%M%S)"
    echo "Backing up audit log to $BACKUP"
    cp "$SKILL_TARGET/audit.log" "$BACKUP"
fi

# Remove skill directory
if [ -d "$SKILL_TARGET" ]; then
    find "$SKILL_TARGET" -type f ! -name "*.backup.*" -delete
    find "$SKILL_TARGET" -type d -empty -delete 2>/dev/null || true
    echo "Skill removed from $SKILL_TARGET"
    echo "  Backups preserved: $SKILL_TARGET/*.backup.*"
else
    echo "Skill not found at $SKILL_TARGET"
fi

# Remove routing rule
if [ -f "$RULES_FILE" ]; then
    rm "$RULES_FILE"
    echo "Routing rule removed: $RULES_FILE"
else
    echo "Routing rule not found at $RULES_FILE"
fi

echo ""
echo "==> Uninstallation complete"
