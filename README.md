# Snowflake AI Kit

Connect your AI coding agent to Snowflake. Plugins for **Claude Code** and **OpenAI Codex** that automatically detect Snowflake prompts and route them to [Cortex Code](https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-cli) — where 55+ built-in skills handle SQL, data governance, dynamic tables, ML, and more.

## Quick Start

### Claude Code

From inside Claude Code:
```
/plugin marketplace add anthropics/claude-plugins-official
/plugin install snowflake-cortex-code
```

Or from your terminal:
```bash
claude plugin marketplace add anthropics/claude-plugins-official
claude plugin install snowflake-cortex-code
```

### OpenAI Codex

From your terminal:
```bash
codex plugin marketplace add Snowflake-Labs/snowflake-ai-kit
codex plugin add snowflake-cortex-code@snowflake-ai-kit
```

Or inside Codex, open `/plugins` and install "Snowflake Cortex Code" from the Snowflake AI Kit marketplace.

### That's it

Ask naturally — the plugin handles routing:

- "Show me my Snowflake warehouses"
- "What databases do I have access to?"
- "Describe the columns in SALES_DATA table"
- "Create a dynamic table that refreshes hourly"

Non-Snowflake prompts ("fix the bug in auth.py", "write a unit test") stay in your current agent.

## How It Works

```
You → Claude Code / Codex → [Plugin detects Snowflake intent] → Cortex Code CLI → Snowflake
```

1. A lightweight keyword filter runs on every prompt (~50ms, no network)
2. If Snowflake intent is detected, the plugin routes to Cortex Code CLI
3. Cortex Code executes with 55+ specialized skills (SQL, governance, ML, streaming, etc.)
4. Results flow back to your agent session

To explicitly invoke Cortex Code (bypassing auto-detection):

```
$cortex-run show me my warehouses and their current state
```

> *See [`plugins/cortex-code/`](plugins/cortex-code/) for full documentation on security model, envelopes, and configuration.*

## Prerequisites

The plugin requires [Cortex Code CLI](https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-cli) (`cortex`) on your PATH. Install it with:

```bash
# One-command installer (also installs Snowflake CLI)
git clone https://github.com/Snowflake-Labs/snowflake-ai-kit.git
cd snowflake-ai-kit && bash install.sh
```

Or install Cortex Code CLI directly from the [official docs](https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-cli).

### Snowflake Connection

Cortex Code CLI needs a Snowflake connection configured at `~/.snowflake/connections.toml`:

```bash
snow connection add
```

## Installer

The bundled installer sets up both Snowflake CLI (`snow`) and Cortex Code CLI (`cortex`):

| Platform | Command |
|---|---|
| macOS / Linux | `bash install.sh` |
| Windows | `.\install.ps1` |
| npx (any) | `npx @snowflake-labs/ai-kit` |

| Flag | Description |
|---|---|
| `--check` / `-Check` | Check installation status without installing |
| `--with-claude` / `-WithClaude` | Also install Claude Code CLI + plugin |
| `--with-codex` / `-WithCodex` | Also install OpenAI Codex CLI + plugin |
| `--help` / `-Help` | Show help |

## Skills

Cortex Code CLI ships with 55+ built-in skills that activate automatically based on your prompt:

```bash
cortex skill list
```

Examples: `semantic-view`, `cortex-agent`, `data-quality`, `dynamic-tables`, `cost-intelligence`, `machine-learning`, `iceberg`, `data-governance`, `cortex-ai-functions`, `deploy-to-spcs`, `lineage`, `dbt-projects-on-snowflake`, `snowflake-notebooks`, `security-investigation`, `workload-performance-analysis`.

Skills are organized by source:

| Category | Description |
|---|---|
| **BUNDLED** | Ship with the CLI binary. Updated on `cortex update`. |
| **GLOBAL** | User-installed in `~/.snowflake/cortex/skills/`. Shared across projects. |
| **EXTERNAL** | Added via `cortex skill add <path>` or `cortex skill add owner/repo`. |
| **PROJECT** | Discovered from the current working directory. |

## Troubleshooting

| Problem | Fix |
|---|---|
| `cortex: command not found` | Re-run `bash install.sh` or install from [Cortex Code CLI docs](https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-cli). |
| `snow: command not found` | Ensure `~/.local/bin` is in `$PATH`. Open a new terminal. |
| Connection errors | Run `snow connection add`. Docs: [Specify credentials](https://docs.snowflake.com/en/developer-guide/snowflake-cli/connecting/specify-credentials) |
| Plugin not routing | Verify plugin is enabled in your agent's settings. |
| Installer hangs on Windows | Run PowerShell as Administrator. |

## Contributing

All PRs run CI on **macOS** and **Windows** via GitHub Actions ([`test.yml`](.github/workflows/test.yml)). The full test suite (200 tests) must pass on both platforms.

```bash
bash tests/run-tests.sh --verbose        # macOS / Linux
.\tests\run-tests.ps1 -Verbose           # Windows (PowerShell)
```

## License

Copyright (c) Snowflake Inc. All rights reserved.

Skills are licensed under the [Snowflake Skills License](LICENSE-SKILLS.md). All other content is [Apache 2.0](LICENSE).
