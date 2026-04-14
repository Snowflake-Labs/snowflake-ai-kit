---
description: Run a Cortex Code review that challenges the implementation approach and design choices
argument-hint: '[--wait|--background] [--base <ref>] [--scope auto|working-tree|branch] [-c connection] [focus ...]'
disable-model-invocation: true
allowed-tools: Read, Glob, Grep, Bash(node:*), Bash(git:*), AskUserQuestion
---

Run an adversarial Cortex Code review that questions the chosen implementation and design.

Raw slash-command arguments:
`$ARGUMENTS`

Core constraint:
- This command is review-only.
- Do not fix issues, apply patches, or suggest that you are about to make changes.

Execution mode rules:
- Same as `/cortex-code:review` -- estimate size, ask foreground vs background.

Foreground flow:
```bash
node "${CLAUDE_PLUGIN_ROOT}/scripts/cortex-companion.mjs" adversarial-review $ARGUMENTS
```
Return the command stdout verbatim.

Background flow:
```typescript
Bash({
  command: `node "${CLAUDE_PLUGIN_ROOT}/scripts/cortex-companion.mjs" adversarial-review $ARGUMENTS`,
  description: "Cortex Code adversarial review",
  run_in_background: true
})
```
After launching, tell the user: "Cortex Code adversarial review started in the background. Check `/cortex-code:status` for progress."
