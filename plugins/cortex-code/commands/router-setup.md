---
description: Run Cortex skill discovery and verify auto-routing is operational
argument-hint: '[--json]'
allowed-tools: Bash(python:*), Bash(cortex:*), Bash(which:*)
---

Discover available Cortex Code skills and verify the auto-router is ready.

Raw slash-command arguments:
`$ARGUMENTS`

## Steps

### 1. Check Cortex CLI is available

```bash
which cortex
```

If not found, tell the user to install Cortex Code CLI and stop.

### 2. Run skill discovery

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/router/discover_cortex.py"
```

This enumerates all Cortex skills, reads their SKILL.md frontmatter and trigger patterns, and caches the result to `/tmp/cortex-capabilities.json`.

### 3. Present results

If `--json` is in the arguments, return the raw JSON output.

Otherwise, present a human-readable summary:
- Total skills discovered
- List of skill names grouped by category (if available)
- Cache location and freshness
- Confirmation that auto-routing is operational

If discovery fails, show the error and suggest:
1. Verify `cortex` is on PATH: `which cortex`
2. Check connection: `cortex connections list`
3. Try manually: `cortex skill list`
