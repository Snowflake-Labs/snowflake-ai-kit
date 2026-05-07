# Codex + Cortex Code Setup Guide

This guide explains how to use **OpenAI Codex CLI** with Snowflake-specialized execution through `cortexcode-tool`.

Codex does **not** use a skill-directory install for this integration. The supported Codex path is the standalone `cortexcode-tool` CLI installed by `integrations/codex/install.sh`.

## Architecture

```text
Codex CLI
  ├─ General coding, local files, git, and non-Snowflake work → Codex tools
  └─ Snowflake-specific work → cortexcode-tool → Cortex Code CLI → Snowflake
```

Codex remains the user-facing orchestrator. For Snowflake questions, Codex should ask for approval in chat, then run `cortexcode-tool` as a foreground command with `--yes`.

## Prerequisites

- Codex CLI installed and working
- Cortex Code CLI installed and configured (`which cortex` returns a path)
- An active Cortex/Snowflake connection (`cortex connections list` shows `active_connection`)
- Python 3.8+ with PyYAML available

## Install

From the repository root:

```bash
bash integrations/codex/install.sh
```

The installer:

1. Installs or refreshes `cortexcode-tool` in `~/.local/bin/`
2. Copies the Python package to `~/.local/lib/cortexcode-tool/`
3. Auto-detects the active Cortex connection
4. Writes the Codex config to `~/.local/lib/cortexcode-tool/config.yaml`

`cortexcode-tool` auto-detects the co-located config, so Codex does not need a `--config` flag.

## Verify Outside Codex

```bash
cortexcode-tool --version
cortexcode-tool --validate-config
cortexcode-tool --envelope RO "How many databases do I have in Snowflake?"
```

The direct terminal query may prompt for approval. Answer the terminal prompt to complete the smoke test.

## Use Inside Codex

For a Snowflake request, Codex should:

1. Identify the request as Snowflake-specific.
2. Ask the user to approve the planned Cortex Code execution.
3. After approval, run a foreground command with `--yes`.

Example approved command:

```bash
cortexcode-tool --yes --envelope RO "How many databases do I have in Snowflake?"
```

Use `RO` for read-only questions, `RW` for data modifications, `RESEARCH` for exploratory work, and `DEPLOY` only for deployment-style operations. Destructive shell command patterns remain blocked by the wrappers even for broader envelopes.

## Expected Codex Behavior

When the user asks:

```text
How many databases do I have in Snowflake?
```

Expected behavior:

- Codex routes the Snowflake question to `cortexcode-tool`.
- Codex asks for approval before execution.
- After approval, Codex runs `cortexcode-tool --yes ...` in the foreground.
- The wrapper invokes Cortex with `cortex -p ... --output-format stream-json`.
- The wrapper does not add `--input-format`.
- The result reports the Snowflake answer back in Codex.

## Configuration

Codex config lives here:

```text
~/.local/lib/cortexcode-tool/config.yaml
```

Important defaults:

```yaml
security:
  approval_mode: "prompt"
  audit_log_path: "~/.cache/cortexcode-tool/audit.log"
  cache_dir: "~/.cache/cortexcode-tool"

cortex:
  connection_name: "<auto-detected active connection>"
  default_envelope: "RO"
```

Keep `approval_mode: "prompt"` for interactive Codex use. Only use `auto` or `envelope_only` for explicitly trusted automation.

## Troubleshooting

### `cortexcode-tool` not found

```bash
bash integrations/codex/install.sh
export PATH="$HOME/.local/bin:$PATH"
```

### Wrong Snowflake connection

```bash
cortex connections list
vi ~/.local/lib/cortexcode-tool/config.yaml
```

Update `cortex.connection_name` to the desired connection.

### Codex reports network sandbox approval is required

Approve the planned Cortex Code execution in Codex chat, then retry the same foreground command with `--yes`.

### Empty Cortex response or only an init event

Verify the wrapper command does not include `--input-format`:

```bash
rg -- '--input-format' scripts shared integrations/cli-tool/cortexcode_tool
```

Docs or tests may mention `--input-format` as a historical anti-pattern, but executable wrappers must not combine it with `-p`.

## Uninstall

```bash
bash integrations/codex/uninstall.sh
```

This removes the Codex CLI integration files for `cortexcode-tool`. It does not remove Cortex Code itself.
