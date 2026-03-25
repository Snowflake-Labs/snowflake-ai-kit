#!/usr/bin/env bash
# Syncs all SKILL.md files to agent rule directories.
#
# Agent directories:
#   .cursor/rules/*.mdc
#   .claude/rules/*.md
#   .windsurf/rules/*.md
#   .gemini/*.md
#
# Usage:
#   .github/scripts/sync-agent-rules.sh          # Sync all
#   .github/scripts/sync-agent-rules.sh --check   # Check if in sync (exit 1 if not)

set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

CHECK_ONLY=false
[[ "${1:-}" == "--check" ]] && CHECK_ONLY=true

# Collect all skill SKILL.md paths (excluding TEMPLATE)
skills=""
for f in snowflake-skills/*/SKILL.md general-skills/*/SKILL.md; do
  [[ -f "$f" ]] || continue
  case "$f" in *TEMPLATE*) continue ;; esac
  skills="$skills $f"
done

# Sync to each agent directory
for agent_config in "cursor:.cursor/rules:mdc" "claude:.claude/rules:md" "windsurf:.windsurf/rules:md" "gemini:.gemini:md"; do
  IFS=: read -r agent dir ext <<< "$agent_config"
  mkdir -p "$dir"
  for src in $skills; do
    name=$(basename "$(dirname "$src")")
    cp "$src" "$dir/${name}.${ext}"
  done
done

if $CHECK_ONLY; then
  if ! git diff --quiet .cursor/rules/ .claude/rules/ .windsurf/rules/ .gemini/; then
    echo "Agent rule files are out of sync with SKILL.md sources."
    echo "Run: .github/scripts/sync-agent-rules.sh"
    exit 1
  fi
  echo "Agent rules are in sync."
else
  echo "Synced agent rules for: cursor, claude, windsurf, gemini"
fi
