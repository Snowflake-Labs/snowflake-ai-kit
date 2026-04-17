#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SKILL_SRC="$REPO_ROOT/agent-to-agent-skills/claude-cortex-code-router"
SKILL_TARGET="$HOME/.cursor/skills-cursor/cortex-code"
RULES_DIR="$HOME/.cursor/rules"

echo "==> Installing Cortex Code skill for Cursor..."
echo ""

# ── Step 1: Verify skill source exists ─────────────────────────────────
if [ ! -f "$SKILL_SRC/SKILL.md" ]; then
    echo "Error: Skill source not found at $SKILL_SRC"
    echo "Make sure you're running this from the snowflake-ai-kit repo."
    exit 1
fi

# ── Step 2: Install skill files ────────────────────────────────────────
echo "Copying skill to $SKILL_TARGET..."
mkdir -p "$SKILL_TARGET/scripts" "$SKILL_TARGET/security/policies" "$SKILL_TARGET/references"

# Core skill files
cp "$SKILL_SRC/SKILL.md" "$SKILL_TARGET/"
cp "$SKILL_SRC/README.md" "$SKILL_TARGET/"
cp "$SKILL_SRC/config.yaml.example" "$SKILL_TARGET/"

# Scripts
for f in discover_cortex.py execute_cortex.py predict_tools.py \
         read_cortex_sessions.py route_request.py security_wrapper.py; do
    [ -f "$SKILL_SRC/scripts/$f" ] && cp "$SKILL_SRC/scripts/$f" "$SKILL_TARGET/scripts/"
done

# Security module
for f in __init__.py approval_handler.py audit_logger.py \
         cache_manager.py config_manager.py prompt_sanitizer.py; do
    [ -f "$SKILL_SRC/security/$f" ] && cp "$SKILL_SRC/security/$f" "$SKILL_TARGET/security/"
done
[ -f "$SKILL_SRC/security/policies/default_policy.yaml" ] && \
    cp "$SKILL_SRC/security/policies/default_policy.yaml" "$SKILL_TARGET/security/policies/"

# References
for f in cortex-cli-reference.md routing-examples.md; do
    [ -f "$SKILL_SRC/references/$f" ] && cp "$SKILL_SRC/references/$f" "$SKILL_TARGET/references/"
done

# Security docs
[ -f "$SKILL_SRC/SECURITY.md" ] && cp "$SKILL_SRC/SECURITY.md" "$SKILL_TARGET/"

# Make scripts executable
chmod +x "$SKILL_TARGET/scripts/"*.py 2>/dev/null || true

# ── Step 3: Install routing rule ───────────────────────────────────────
echo "Installing Cursor routing rule..."
mkdir -p "$RULES_DIR"
cp "$SCRIPT_DIR/cortex-snowflake-routing.mdc" "$RULES_DIR/"

# ── Step 4: Summary ───────────────────────────────────────────────────
echo ""
echo "==> Installation complete"
echo ""
echo "  Skill   : $SKILL_TARGET/"
echo "  Rule    : $RULES_DIR/cortex-snowflake-routing.mdc"
echo ""
echo "Restart Cursor for changes to take effect."
echo "Test with: Ask any Snowflake question — Cursor routes it automatically."
