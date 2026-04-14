---
description: Run a dbt model review (materialization, testing, lineage, Snowflake patterns)
argument-hint: '[--wait|--background] [--base <ref>] [--scope auto|working-tree|branch] [-c connection] [focus ...]'
disable-model-invocation: true
allowed-tools: Read, Glob, Grep, Bash(node:*), Bash(git:*), AskUserQuestion
---

Run a Cortex Code review focused on dbt models, materialization strategy, testing coverage, and Snowflake-specific patterns.

Raw slash-command arguments:
`$ARGUMENTS`

Core constraint:
- This command is review-only. Do not fix issues or apply patches.

Execution mode rules:
- Same as `/cortex-code:review` -- estimate size, ask foreground vs background.

Foreground flow:
```bash
node "${CLAUDE_PLUGIN_ROOT}/scripts/cortex-companion.mjs" dbt-review $ARGUMENTS
```
Return the command stdout verbatim.

Background flow:
```typescript
Bash({
  command: `node "${CLAUDE_PLUGIN_ROOT}/scripts/cortex-companion.mjs" dbt-review $ARGUMENTS`,
  description: "Cortex Code dbt review",
  run_in_background: true
})
```
After launching, tell the user: "Cortex Code dbt review started in the background. Check `/cortex-code:status` for progress."
