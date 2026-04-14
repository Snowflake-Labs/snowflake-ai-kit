---
description: Run a Snowflake SQL optimization review (performance, anti-patterns, cost)
argument-hint: '[--wait|--background] [--base <ref>] [--scope auto|working-tree|branch] [-c connection] [focus ...]'
disable-model-invocation: true
allowed-tools: Read, Glob, Grep, Bash(node:*), Bash(git:*), AskUserQuestion
---

Run a Cortex Code review focused on Snowflake SQL performance, anti-patterns, and cost optimization.

Raw slash-command arguments:
`$ARGUMENTS`

Core constraint:
- This command is review-only. Do not fix issues or apply patches.

Foreground flow:
```bash
node "${CLAUDE_PLUGIN_ROOT}/scripts/cortex-companion.mjs" sql-review $ARGUMENTS
```
Return the command stdout verbatim.

Background flow:
```typescript
Bash({
  command: `node "${CLAUDE_PLUGIN_ROOT}/scripts/cortex-companion.mjs" sql-review $ARGUMENTS`,
  description: "Cortex Code SQL review",
  run_in_background: true
})
```
