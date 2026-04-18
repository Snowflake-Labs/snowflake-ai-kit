---
description: Check whether the local Cortex Code CLI is installed and ready, and discover available Cortex skills for auto-routing
argument-hint: '[--json]'
allowed-tools: Bash(node:*), Bash(python:*)
---

Run the companion setup check:

```bash
node "${CLAUDE_PLUGIN_ROOT}/scripts/cortex-companion.mjs" setup --json $ARGUMENTS
```

Present the setup output to the user.
If Cortex Code is not installed, tell the user how to install it.

Then run router skill discovery so auto-routing is ready:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/router/discover_cortex.py"
```

If discovery succeeds, tell the user how many Cortex skills were found and that auto-routing is active.
If discovery fails (e.g. cortex not on PATH), note that auto-routing is not available but slash commands still work.
