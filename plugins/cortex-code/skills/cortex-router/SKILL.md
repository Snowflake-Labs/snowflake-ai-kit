---
name: cortex-router
description: Auto-routing skill loaded by the prompt filter hook. Routes Snowflake-related operations to Cortex Code CLI. Not for direct invocation — use $cortex-run instead.
user-invocable: false
metadata:
  author: Snowflake Integration Team
  version: 3.0.0
  compatibility: Requires Cortex Code CLI installed and configured
---

# Cortex Code Router

Route Snowflake operations to Cortex Code CLI, which has specialized bundled skills
(data-quality, semantic-view, cost-intelligence, ML, governance, etc.).

**CRITICAL: Follow steps 1 → 2 → 3 in order. Do NOT skip to Step 3.**

## Step 1: Verify CLI

```bash
which cortex 2>/dev/null && cortex --version
```

If `cortex` is NOT found:
1. Tell the user: "Cortex Code CLI is not installed. Setting it up now."
2. Load the `cortex-code:cortex-setup` skill using the Skill tool.
3. **STOP** — do not continue until the CLI is installed.

## Step 2: Confirm Routing

Run the routing script to check if this prompt should go to Cortex or stay in Claude Code:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/router/route_request.py" --prompt "USER_PROMPT_HERE"
```

Replace `USER_PROMPT_HERE` with the actual user prompt (shell-escaped).

**Read the output carefully:**
- If output says **"route: cortex"** → proceed to Step 3
- If output says **"route: claude"** → **STOP**. Handle the request yourself using Claude Code tools (sql_execute, Read, Write, etc.). Do NOT run execute_cortex.py.

## Step 3: Execute via Cortex Code

Only reach this step if Step 2 confirmed routing to Cortex.

Choose a security envelope:
- **RO**: Read-only queries (SELECT, SHOW, DESCRIBE) — use this for most queries
- **RW**: Data modifications (INSERT, UPDATE, CREATE, etc.)
- **RESEARCH**: Read + web access, no writes
- **DEPLOY**: Full access (use sparingly)

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/router/execute_cortex.py" \
  --prompt "USER_PROMPT_HERE" \
  --envelope "RO" \
  --approval-mode "auto"
```

Add `--connection CONNECTION_NAME` if a specific Snowflake connection is needed.

**Timeout**: This command may take 30-90 seconds. If it takes longer than 2 minutes, it likely hung — kill the process and tell the user to try `$cortex-run` for direct invocation.

## Step 4: Return Results

Format Cortex's output for the user:
- Show SQL results in readable tables
- Display any generated artifacts or analysis
- Report success/failure clearly

## Notes

- Each Cortex invocation is **stateless** — context must be in the prompt
- Cortex has bundled skills for: data-quality, semantic-view, cost-intelligence, ML, governance, security, lineage, dynamic-tables, and more
- For simple SQL queries that don't need Cortex skills, Step 2 should route to Claude Code
- If `route_request.py` is missing or fails, fall back to Claude Code tools
