---
name: cortex-code-runtime
description: Internal helper contract for calling the Cortex Code companion runtime from Claude Code
user-invocable: false
---

# Cortex Code Runtime

Primary helper:
- `node "${CLAUDE_PLUGIN_ROOT}/scripts/cortex-companion.mjs" task "<raw arguments>"`

Execution rules:
- The rescue subagent is a forwarder, not an orchestrator.
- Invoke `task` once and return stdout unchanged.
- Do not call `setup`, `review`, `adversarial-review`, `status`, `result`, or `cancel` from the rescue subagent.
- Default to `--write` unless the user explicitly asks for read-only behavior.
