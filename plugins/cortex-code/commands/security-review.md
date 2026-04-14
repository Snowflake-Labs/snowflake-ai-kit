---
description: Run a Snowflake security review (RBAC, credentials, data governance, access policies)
argument-hint: '[--wait|--background] [--base <ref>] [--scope auto|working-tree|branch] [-c connection] [focus ...]'
disable-model-invocation: true
allowed-tools: Read, Glob, Grep, Bash(node:*), Bash(git:*), AskUserQuestion
---

Run a Cortex Code review focused on Snowflake security: RBAC, credentials, data governance, and access policies.

Raw slash-command arguments:
`$ARGUMENTS`

Core constraint:
- This command is review-only. Do not fix issues or apply patches.

Foreground flow:
```bash
node "${CLAUDE_PLUGIN_ROOT}/scripts/cortex-companion.mjs" security-review $ARGUMENTS
```
Return the command stdout verbatim.

Background flow:
```typescript
Bash({
  command: `node "${CLAUDE_PLUGIN_ROOT}/scripts/cortex-companion.mjs" security-review $ARGUMENTS`,
  description: "Cortex Code security review",
  run_in_background: true
})
```
