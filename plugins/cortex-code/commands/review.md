---
description: Run a Cortex Code review against local git state
argument-hint: '[--wait|--background] [--base <ref>] [--scope auto|working-tree|branch] [-c connection]'
disable-model-invocation: true
allowed-tools: Read, Glob, Grep, Bash(node:*), Bash(git:*), AskUserQuestion
---

Run a Cortex Code review on the current working tree or branch diff.

Raw slash-command arguments:
`$ARGUMENTS`

Core constraint:
- This command is review-only.
- Do not fix issues, apply patches, or suggest that you are about to make changes.
- Your only job is to run the review and return the output verbatim to the user.

Execution mode rules:
- If the raw arguments include `--wait`, run in the foreground.
- If the raw arguments include `--background`, run in a Claude background task.
- Otherwise, estimate the review size:
  - Use `git status --short` and `git diff --shortstat` to gauge size.
  - Recommend waiting only for clearly tiny reviews (1-2 files).
  - Otherwise recommend background.
- Use `AskUserQuestion` exactly once with two options, putting the recommended option first and suffixing its label with `(Recommended)`:
  - `Wait for results`
  - `Run in background`

Foreground flow:
```bash
node "${CLAUDE_PLUGIN_ROOT}/scripts/cortex-companion.mjs" review $ARGUMENTS
```
Return the command stdout verbatim. Do not paraphrase, summarize, or fix issues.

Background flow:
```typescript
Bash({
  command: `node "${CLAUDE_PLUGIN_ROOT}/scripts/cortex-companion.mjs" review $ARGUMENTS`,
  description: "Cortex Code review",
  run_in_background: true
})
```
After launching, tell the user: "Cortex Code review started in the background. Check `/cortex-code:status` for progress."
