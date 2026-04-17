# Cortex Code for Codex — CLI Install

Enables Codex to run Snowflake queries via the `cortexcode-tool` CLI.

Codex does not use a skill directory. Instead, `cortexcode-tool` is installed as a standalone CLI that Codex calls directly as a foreground command.

## Why CLI instead of skill?

Codex's sandbox blocks the interactive approval prompts that `cortex -p` requires without `--bypass`. The `cortexcode-tool` wraps `cortex` with `--bypass` and `approval_mode: auto`, making it safe and reliable in non-TTY environments.

## Prerequisites

- Codex CLI installed
- Cortex Code CLI installed and configured (`which cortex`)
- Active Snowflake connection (`cortex connections list`)
- Python 3.8+

## Install

**Option A — From repo:**

```bash
git clone https://github.com/Snowflake-Labs/snowflake-ai-kit.git
cd snowflake-ai-kit
bash integrations/codex/install.sh
```

**Option B — Via the unified installer:**

```bash
bash install.sh --with-codex
```

Both methods:
1. Install `cortexcode-tool` CLI to `~/.local/bin/`
2. Auto-detect your active Cortex connection
3. Write Codex-optimized config to `~/.local/lib/cortexcode-tool/config.yaml`

## Verify

```bash
cortexcode-tool --version
cortexcode-tool "How many databases do I have in Snowflake?" --envelope RO
```

## Usage from Codex

First time — paste into a Codex session to confirm the tool is discoverable:

```
which cortexcode-tool
cortexcode-tool --help
```

Once discovered, Codex invokes `cortexcode-tool` for Snowflake questions automatically.

```bash
# Explicit
cortexcode-tool "How many databases do I have in Snowflake?"

# Implicit — Codex detects Snowflake intent and calls cortexcode-tool
How many databases do I have in Snowflake?
```

Do **not** background the command. Codex waits for foreground commands (30-90s is normal).

## Uninstall

```bash
bash integrations/codex/uninstall.sh
# or
bash integrations/cli-tool/uninstall.sh
```

## Troubleshooting

**`cortexcode-tool` not found:** Re-run `bash integrations/codex/install.sh` and ensure `~/.local/bin` is in PATH.

**Command hangs in Codex:** Verify `approval_mode: "auto"` in `~/.local/lib/cortexcode-tool/config.yaml`.

**Wrong connection:** Edit `~/.local/lib/cortexcode-tool/config.yaml` or re-run install to auto-detect.
