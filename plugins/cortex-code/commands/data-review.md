---
description: Run a Snowflake data engineering review (SQL, pipelines, schema, warehouse cost)
argument-hint: '[--wait|--background] [--base <ref>] [--scope auto|working-tree|branch] [-c connection] [focus ...]'
disable-model-invocation: true
allowed-tools: Read, Glob, Grep, Bash(node:*), Bash(git:*), AskUserQuestion
---

Run a Cortex Code data engineering review focused on Snowflake SQL, pipelines, and warehouse patterns.

Raw slash-command arguments:
`$ARGUMENTS`

Core constraint:
- This command is review-only. Do not fix issues or apply patches.

Execution mode rules:
- Same as `/cortex-code:review` -- estimate size, ask foreground vs background.

Foreground flow:
```bash
node "${CLAUDE_PLUGIN_ROOT}/scripts/cortex-companion.mjs" data-review $ARGUMENTS
```
Return the command stdout verbatim.

Background flow:
```typescript
Bash({
  command: `node "${CLAUDE_PLUGIN_ROOT}/scripts/cortex-companion.mjs" data-review $ARGUMENTS`,
  description: "Cortex Code data review",
  run_in_background: true
})
```
After launching, tell the user: "Cortex Code data review started in the background. Check `/cortex-code:status` for progress."
