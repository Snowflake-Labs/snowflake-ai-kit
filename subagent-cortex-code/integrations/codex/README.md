# Cortex Code for Codex — CLI Install

Enables Codex to run Snowflake queries via the `cortexcode-tool` CLI.

Codex does not use a skill directory for this integration. Instead, `cortexcode-tool` is installed as a standalone CLI that Codex calls directly as a foreground command.

## Why CLI instead of skill?

Codex uses `cortexcode-tool` as a standalone foreground command. The Codex-specific config defaults to `approval_mode: prompt` with the restrictive `RO` envelope so Snowflake reads require explicit approval before execution.

## Prerequisites

- Codex CLI installed
- Cortex Code CLI installed and configured (`which cortex` should return a path)
- Active Snowflake connection (`cortex connections list`)
- Python 3.8+

## Install

```bash
git clone https://github.com/Snowflake-Labs/subagent-cortex-code.git
cd subagent-cortex-code
bash integrations/codex/install.sh
```

The script:
1. Installs `cortexcode-tool` CLI to `~/.local/bin/` (via `integrations/cli-tool/setup.sh`)
2. Auto-detects your active Cortex connection from `cortex connections list`
3. Writes config to `~/.local/lib/cortexcode-tool/config.yaml` (auto-detected — no `--config` flag needed)

## Verify

```bash
cortexcode-tool --version
cortexcode-tool --envelope RO "How many databases do I have in Snowflake?"
```

Expected: the direct terminal query may ask for approval, then runs for 30–90 seconds and prints formatted results. Inside Codex chat, approve the planned execution first, then Codex should retry with `--yes`.

## Usage from Codex

**First time**: paste these into a Codex session to confirm the tool is discoverable:

```
which cortexcode-tool
cortexcode-tool --help
```

Once discovered, Codex will invoke `cortexcode-tool` for Snowflake questions automatically. You can be explicit or implicit — both work:

```bash
# Explicit after Codex chat approval
cortexcode-tool --yes --envelope RO "How many databases do I have in Snowflake?"

# Implicit — Codex detects the Snowflake intent and calls cortexcode-tool on its own
How many databases do I have in Snowflake?
```

No need to specify `--envelope` in your prompts. Codex selects the appropriate envelope based on the operation.
Use `--yes` only after Codex has shown the planned Cortex Code execution and the user has approved it in chat.

Do **not** background the command (`& disown`). Codex automatically waits for foreground commands to complete (30–90 seconds is normal).

## What gets installed

```
~/.local/bin/cortexcode-tool              # CLI entry point
~/.local/lib/cortexcode-tool/             # Python package
~/.local/lib/cortexcode-tool/config.yaml  # Config (auto-detected by the tool)
```

Config example:
```yaml
security:
  approval_mode: "prompt"
  audit_log_path: "~/.cache/cortexcode-tool/audit.log"
  cache_dir: "~/.cache/cortexcode-tool"

cortex:
  connection_name: "your-connection-name"
  default_envelope: "RO"

logging:
  file: "~/.cache/cortexcode-tool/cortexcode-tool.log"
```

Audit/log paths use `~/.cache/cortexcode-tool/` so logs stay outside the repository. If Codex reports that network access is required, approve the planned Cortex Code execution in chat and retry the same foreground command with `--yes`.

## Security notes

- `approval_mode` defaults to `prompt`; user config cannot relax this unless organization policy explicitly authorizes the relaxed field/value.
- `RO` is the default envelope for Codex reads.
- Requested envelopes are checked against `security.allowed_envelopes` before routing, approval, or Cortex execution.
- `NONE` is rejected before Cortex execution.
- `DEPLOY` requires explicit confirmation and blocks Bash/destructive shell.
- Output files are constrained under `CORTEX_CODE_OUTPUT_DIR` or the current working directory.
- Installers use private permissions (`0700` directories and `0600` sensitive config files).

## Update connection

If you switch Cortex connections:
```bash
# Re-run install to auto-detect new active connection
bash integrations/codex/install.sh

# Or edit manually
vi ~/.local/lib/cortexcode-tool/config.yaml
```

## Uninstall

```bash
bash integrations/codex/uninstall.sh
```

## Troubleshooting

**`cortexcode-tool` not found:**
```bash
which cortexcode-tool
# If missing, re-run: bash integrations/codex/install.sh
# Also ensure ~/.local/bin is in PATH
export PATH="$HOME/.local/bin:$PATH"
```

**Command waits or needs network approval in Codex:**
```bash
# Verify approval_mode is prompt by default
cat ~/.local/lib/cortexcode-tool/config.yaml | grep approval_mode
# Must be: approval_mode: "prompt"

# Verify Cortex connection works
cortex connections list
cortex -p "SHOW DATABASES;" --output-format stream-json
```

**Wrong connection used:**
```bash
# Check which connection is active
cortex connections list
# Edit config
vi ~/.local/lib/cortexcode-tool/config.yaml  # update connection_name
```

**Network sandbox approval required:**
Approve the planned Cortex Code execution in Codex chat, then retry the same foreground command with `--yes`. Do not background the command.
