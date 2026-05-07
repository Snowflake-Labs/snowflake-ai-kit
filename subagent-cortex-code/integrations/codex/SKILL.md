---
name: cortex-code
description: Routes Snowflake-related operations to Cortex Code CLI for specialized Snowflake expertise. Use when the user asks about Snowflake databases, warehouses, schemas, tables, SQL on Snowflake, Cortex AI features, Snowpark, dynamic tables, streams, tasks, governance, or Snowflake security. Do not use for general programming, local file operations, non-Snowflake databases, web development, or infrastructure unrelated to Snowflake.
license: Proprietary. See LICENSE for complete terms
metadata:
  author: Snowflake Integration Team
  compatibility: Requires Cortex Code CLI installed and configured
---

# Cortex Code Integration for Codex

This skill lets Codex delegate Snowflake-specific work to Cortex Code via the `cortexcode-tool` CLI while Codex remains the primary assistant for general coding and local repository tasks.

## Routing Principle

Only Snowflake-specific operations go to Cortex Code. Everything else stays in Codex. The cortexcode-tool automatically handles routing.

## How to use this skill

When this skill triggers, follow this workflow.

### 1. Execute Snowflake queries via cortexcode-tool

Ask the user for approval in Codex before execution. After approval, run
`cortexcode-tool` as a **foreground command** with `--yes` — do NOT background it
with `&`. Codex automatically waits for long-running commands ("Waited for
background terminal"). The command takes 30-90 seconds.

```bash
cortexcode-tool --yes "USER_PROMPT_HERE" --envelope RO --config ~/.local/lib/cortexcode-tool/config.yaml
```

Choose envelope based on operation:
- `RO` for read-only queries (default for most operations)
- `RW` for data modifications or writes
- `RESEARCH` for exploratory work
- `DEPLOY` for deployment operations

**IMPORTANT**: Do not call `cortex -p` directly — it requires interactive stdin and will hang.
**IMPORTANT**: Do not use `& disown` or background execution — Codex cannot track orphaned processes.
**IMPORTANT**: Do not use `--yes` until the user has approved the planned Cortex Code execution in Codex chat.
**IMPORTANT**: If `cortexcode-tool` says it requires network access, ask the user to approve the planned Cortex Code execution in Codex chat and retry with `--yes`.

### 2. Present results back in Codex

After cortexcode-tool finishes:
- The tool returns clean, formatted output (not JSON)
- Summarize the result clearly for the user
- Include key findings, SQL, errors, or next actions
- Keep Codex as the user-facing orchestrator

**Example output** (stdout only — routing/debug messages go to stderr):
```
You have **64 databases** in your Snowflake account...
```

### 3. Handle non-Snowflake requests locally

For non-Snowflake requests, handle directly using Codex tools:
- Local file reads/writes/edits
- Git operations
- Web or app development unrelated to Snowflake
- General Python, JavaScript, shell, or infrastructure work
- Non-Snowflake databases

## Security expectations

The cortexcode-tool uses built-in security flow:
- Prompt approval by default (approval_mode: "prompt")
- Audit logging to ~/.cache/cortexcode-tool/audit.log
- Envelope-based tool restrictions
- Prompt sanitization
- Credential path blocking

Config file location: `~/.local/lib/cortexcode-tool/config.yaml` (written by install.sh, persists across reboots)

## Notes for Codex

- Handle local file operations, git, and non-Snowflake work directly - don't use cortexcode-tool
- For Snowflake queries, use cortexcode-tool with appropriate envelope
- Keep context minimal when invoking Cortex
- cortexcode-tool automatically determines if a query is Snowflake-related
- If a query fails routing or times out, handle locally or explain the limitation

## Troubleshooting

### Error: Permission denied on audit log or cache
**Solution**: Use the provided config (audit/cache go to `~/.cache/cortexcode-tool`):
```bash
--config ~/.local/lib/cortexcode-tool/config.yaml
```

### Error: Cortexcode-tool not found
**Solution**: Run the Codex install script — it installs `cortexcode-tool` automatically:
```bash
bash integrations/codex/install.sh
```

### Query takes too long
**Note**: Queries typically take 30-60 seconds. Codex will wait automatically.
If the command times out, retry once — Snowflake connection may have been cold.

### cortex -p hangs with no output
**Cause**: Direct `cortex -p` invocation may wait for interactive approval in non-TTY terminals.
**Solution**: Use `cortexcode-tool`, which invokes Cortex in stream JSON mode with the configured envelope.

## Examples

**Snowflake database count:**
```bash
cortexcode-tool --yes "How many databases do I have in Snowflake?" --envelope RO --config ~/.local/lib/cortexcode-tool/config.yaml
```

**Query specific database:**
```bash
cortexcode-tool --yes "What tables are in DB_STOCK database?" --envelope RO --config ~/.local/lib/cortexcode-tool/config.yaml
```

**Data modification:**
```bash
cortexcode-tool --yes "Create a backup table of SALES_DATA" --envelope RW --config ~/.local/lib/cortexcode-tool/config.yaml
```
