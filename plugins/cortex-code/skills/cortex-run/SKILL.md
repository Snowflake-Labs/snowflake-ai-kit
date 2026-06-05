---
name: cortex-run
description: "ONLY load this skill when the user explicitly types $cortex-run or /cortex-run. NEVER load this skill from auto-routing hooks or keyword matching. For auto-routed prompts, use snowflake-cortex-code:cortex-router instead."
license: Proprietary. See LICENSE-SKILLS.md for complete terms
user-invocable: true
metadata:
  author: Snowflake
  version: 1.0.0
---

# Cortex Code (Explicit Invocation)

Send a prompt directly to Cortex Code CLI, bypassing the auto-routing keyword filter. Use this when the user explicitly wants Cortex Code to handle their request.

## Prerequisites

Cortex Code CLI must be installed and on PATH:

```bash
which cortex && cortex --version
```

If `cortex` is not found, load the `snowflake-cortex-code:cortex-setup` skill to install it. Do NOT proceed without it.

## Workflow

### Step 1: Check Cortex CLI

**This step is mandatory. Do it first, every time.**

```bash
which cortex 2>/dev/null && cortex --version
```

If `cortex` is NOT found or the command fails:
1. Tell the user: "Cortex Code CLI is not installed. Setting it up now."
2. Load the `snowflake-cortex-code:cortex-setup` skill using the Skill tool.
3. Follow its instructions to install the CLI.
4. **STOP here** — do NOT proceed to Step 2 until the CLI is installed and working.

### Step 2: Extract the User Prompt

The user's message after `$cortex-run` is the prompt to send. If the user typed only `$cortex-run` with no additional text, ask what they want to do in Snowflake.

### Step 3: Choose Security Envelope

Pick the envelope based on what the operation needs:

| Envelope | Use when | Blocks |
|----------|----------|--------|
| **RO** | Queries, reads, exploration | Edit, Write, destructive Bash |
| **RW** | Data modifications, DDL | Destructive Bash (rm -rf, sudo) |
| **RESEARCH** | Exploration + web access | Edit, Write, destructive Bash |
| **DEPLOY** | Full access needed | Nothing |

Default to **RW** unless the request is clearly read-only.

### Step 4: Execute via Cortex Code

Run the prompt through the execution script:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/router/execute_cortex.py" \
  --prompt "USER_PROMPT_HERE" \
  --envelope "RW"
```

For read-only queries:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/router/execute_cortex.py" \
  --prompt "USER_PROMPT_HERE" \
  --envelope "RO"
```

To specify a Snowflake connection:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/router/execute_cortex.py" \
  --prompt "USER_PROMPT_HERE" \
  --envelope "RW" \
  --connection "connection_name"
```

### Step 5: Return Results

Format Cortex's output for the user:
- Show SQL results in readable tables
- Display generated artifacts
- Report success or failure
- If Cortex errored, show the error and suggest fixes

## Context Enrichment

Before sending the prompt, prepend relevant context from the current Claude Code conversation:

```
# Context from Claude Code Session
[Last 2-3 relevant exchanges — Snowflake-specific details only]

# User Request
[The original prompt]
```

Keep context minimal — Cortex only sees what you send in each prompt (unless resuming a session).

## Multi-turn: `--resume-last` vs fresh

Every Cortex invocation returns a `session_id` that is persisted automatically. Follow-up
turns can resume that session so Cortex sees the prior conversation — real multi-turn,
not one-shot batches per prompt.

- **Add `--resume-last`** when the current prompt is a continuation of the
  previous Cortex turn: "keep going", "apply the top suggestion", "dig deeper",
  "also show me ...", "and for last quarter", "fix that", or any clarification
  of an answer Cortex just gave.
- **Omit `--resume-last`** (start fresh) when the user switches topics, asks
  about a different database/warehouse, or begins a clearly new task.
- `--resume <session_id>` is also accepted if you have an explicit id.

```bash
# Follow-up on the previous Cortex turn
python "${CLAUDE_PLUGIN_ROOT}/scripts/router/execute_cortex.py" \
  --prompt "also show me the column types" --envelope "RO" \
  --resume-last
```

## Examples

**User**: `$cortex-run show me tables in the RAW schema`
- Envelope: RO
- Prompt: "show me tables in the RAW schema"

**User**: `$cortex-run create a dynamic table that aggregates daily sales`
- Envelope: RW
- Prompt: "create a dynamic table that aggregates daily sales"

**User**: `$cortex-run` (no prompt)
- Ask: "What would you like Cortex Code to do?"

## Notes

- This skill is for **explicit** invocation only. Auto-routing is handled separately by the prompt filter hook + cortex-router skill.
- Use `--resume-last` for follow-up prompts so Cortex retains conversation context. For new topics, omit it and include relevant context in the prompt instead.
- Security envelope enforcement uses `--permission-prompt-tool stdio` — every tool call is gated by `envelope_policy.decide()` at the process boundary.
