---
description: Check whether the local Cortex Code CLI is installed and ready
argument-hint: '[--json]'
allowed-tools: Bash(node:*)
---

Run:

```bash
node "${CLAUDE_PLUGIN_ROOT}/scripts/cortex-companion.mjs" setup --json $ARGUMENTS
```

Present the setup output to the user.
If Cortex Code is not installed, tell the user how to install it.
