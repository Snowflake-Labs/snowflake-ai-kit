---
description: Delegate investigation or a fix to Cortex Code
argument-hint: '[--background|--wait] [--write] [-c connection] [--model model] [--effort effort] [what Cortex Code should investigate or fix]'
allowed-tools: Bash(node:*)
---

Delegate work to Cortex Code by running it as a subprocess.

Raw user request:
$ARGUMENTS

Execution mode:
- If `--background` is present, run in a Claude background task.
- Otherwise run in foreground.

Foreground flow:
```bash
node "${CLAUDE_PLUGIN_ROOT}/scripts/cortex-companion.mjs" task $ARGUMENTS
```
Return the stdout verbatim. Do not paraphrase or add commentary.

Background flow:
```bash
node "${CLAUDE_PLUGIN_ROOT}/scripts/cortex-companion.mjs" task --background $ARGUMENTS
```
Tell the user the job ID and to check `/cortex-code:status`.

If the user did not supply a request, ask what Cortex Code should investigate or fix.
