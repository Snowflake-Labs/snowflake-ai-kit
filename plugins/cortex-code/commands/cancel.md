---
description: Cancel an active background Cortex Code job
argument-hint: '[job-id]'
disable-model-invocation: true
allowed-tools: Bash(node:*)
---

!`node "${CLAUDE_PLUGIN_ROOT}/scripts/cortex-companion.mjs" cancel $ARGUMENTS`
