# Cortexcode Tool — CLI

A standalone CLI that brings Cortex Code's Snowflake expertise to VSCode, Windsurf, terminal, and any environment without a skills-based agent.

> **Claude Code and Cursor** use the skill-based integration via `npx skills add`. This CLI is for other environments.
> **Codex** installs this tool via `bash integrations/codex/install.sh` (which also writes the Codex-specific prompt/RO config).

## Supported environments

- VSCode (task runner + code snippets)
- Windsurf
- Terminal (any shell)
- Codex (via `integrations/codex/install.sh`)

## Install

```bash
git clone https://github.com/Snowflake-Labs/subagent-cortex-code.git
cd subagent-cortex-code/integrations/cli-tool
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

See `config.yaml.example` for all options. Keep `approval_mode: "prompt"` for
interactive use; reserve `auto` or `envelope_only` for explicitly trusted
automation enabled by organization policy. User config cannot relax approval
mode or expand allowed envelopes unless organization policy explicitly
authorizes that field/value. Output files are constrained under
`CORTEX_CODE_OUTPUT_DIR` or the current working directory. Installers use
private permissions (`0700` directories and `0600` sensitive config files).

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
- `RO` — read-only (blocks writes and Bash)
- `RW` — read-write (blocks Bash and destructive shell patterns)
- `RESEARCH` — read + web access (blocks writes and Bash)
- `DEPLOY` — deployment operations; requires explicit confirmation and blocks Bash/destructive shell
- `NONE` — rejected before Cortex execution

`cortexcode-tool` checks the requested envelope against `security.allowed_envelopes`
before routing, approval, or Cortex execution.

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

**Command waits for approval:**
```bash
# Check approval mode
cat ~/.local/lib/cortexcode-tool/config.yaml | grep approval_mode
```
For direct terminal use, answer the approval prompt. For Codex, ask the user to
approve the planned Cortex Code execution in chat, then run the same foreground
command with `--yes`. Keep `approval_mode: "prompt"` unless you have an explicit
trusted automation requirement.

---

Copyright © 2026 Snowflake Inc. All rights reserved.
