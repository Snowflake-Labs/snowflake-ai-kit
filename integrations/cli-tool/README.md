# Cortexcode Tool — CLI

A standalone CLI that wraps Cortex Code for environments that don't support plugin/skill-based routing (Codex, terminal, CI/CD).

> **Claude Code** uses the [plugin](../../plugins/cortex-code/) instead of this CLI.
> **Codex** installs this tool via `bash integrations/codex/install.sh` (which also writes the right config for Codex's sandbox).

## Supported environments

- VSCode (task runner + code snippets)
- Windsurf
- Terminal (any shell)
- Codex (via `integrations/codex/install.sh`)

## Install

```bash
git clone https://github.com/Snowflake-Labs/snowflake-ai-kit.git
cd snowflake-ai-kit/integrations/cli-tool
bash setup.sh
```

Installs `cortexcode-tool` to `~/.local/bin/`. Ensure `~/.local/bin` is in your `PATH`.

**Verify:**
```bash
cortexcode-tool --version
cortexcode-tool "How many databases do I have in Snowflake?"
```

## Prerequisites

- Python 3.8+
- Cortex Code CLI v1.0.42+ installed (`which cortex`)
- Active Snowflake connection (`cortex connections list`)

## Configuration

`setup.sh` writes config to `~/.local/lib/cortexcode-tool/config.yaml` automatically (co-located with the installed package). You can also place a config at `~/.config/cortexcode-tool/config.yaml` as a fallback — the tool checks the lib directory first.

To customize, edit the auto-written config or create one from the example:

```bash
cp config.yaml.example ~/.local/lib/cortexcode-tool/config.yaml
# edit as needed
```

Key settings:
```yaml
security:
  approval_mode: "prompt"  # or "auto" or "envelope_only"

cortex:
  connection_name: "your-connection-name"
  default_envelope: "RO"
```

See `config.yaml.example` for all options.

## Usage

```bash
# Query Snowflake
cortexcode-tool "Show me top 10 customers by revenue"

# Specify security envelope
cortexcode-tool "List all databases" --envelope RO
cortexcode-tool "Create a backup table" --envelope RW

# Specify connection
cortexcode-tool "your question" --connection my-snowflake-connection
```

Envelopes:
- `RO` — read-only (blocks writes)
- `RW` — read-write (blocks destructive ops)
- `RESEARCH` — read + web access
- `DEPLOY` — full access

## Package structure

```
cortexcode-tool/
├── cortexcode_tool/          # Python package
│   ├── core/                 # Routing, execution, discovery
│   ├── security/             # Approval, audit, cache, sanitization
│   └── ide_adapters/         # VSCode, Cursor adapter
├── setup.sh                  # Install to ~/.local/bin/
├── uninstall.sh
└── config.yaml.example       # Configuration template
```

## Uninstall

```bash
bash uninstall.sh
```

## Troubleshooting

**`cortexcode-tool` not found:**
```bash
# Add ~/.local/bin to PATH
export PATH="$HOME/.local/bin:$PATH"
# Re-run setup
bash setup.sh
```

**No active connection:**
```bash
cortex connections list
cortex connections create
```

**Command hangs (approval prompt):**
```bash
# Check approval mode
cat ~/.local/lib/cortexcode-tool/config.yaml | grep approval_mode
# For automated use, set: approval_mode: "auto"
```

---

Copyright © 2026 Snowflake Inc. All rights reserved.
