---
description: Show active and recent Cortex Code jobs for this repository
argument-hint: '[job-id] [--all]'
disable-model-invocation: true
allowed-tools: Bash(node:*)
---

!`node "${CLAUDE_PLUGIN_ROOT}/scripts/cortex-companion.mjs" status $ARGUMENTS`

Present the command output to the user. Keep it compact.
