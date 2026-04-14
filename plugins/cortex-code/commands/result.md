---
description: Show the stored final output for a finished Cortex Code job
argument-hint: '[job-id]'
disable-model-invocation: true
allowed-tools: Bash(node:*)
---

!`node "${CLAUDE_PLUGIN_ROOT}/scripts/cortex-companion.mjs" result $ARGUMENTS`

Present the full command output to the user. Do not summarize or condense it.
