# Snowflake AI Kit

Connect your AI coding agent to Snowflake. One plugin, for **Claude Code**, **OpenAI Codex**, and **Devin CLI**, automatically detects Snowflake prompts and routes them to [Cortex Code](https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-cli) — where 55+ built-in skills handle SQL, data governance, dynamic tables, ML, and more. A separate **Devin** plugin connects through a Snowflake Managed MCP Server instead, with no local Cortex Code CLI.

[![Claude Code](https://img.shields.io/badge/Claude%20Code-Marketplace-8A2BE2)](https://claude.com/plugins/snowflake-cortex-code)
[![OpenAI Codex](https://img.shields.io/badge/OpenAI%20Codex-Marketplace-orange)](https://github.com/Snowflake-Labs/snowflake-ai-kit#openai-codex)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue)](LICENSE)
[![CI](https://img.shields.io/github/actions/workflow/status/Snowflake-Labs/snowflake-ai-kit/test.yml?label=CI)](https://github.com/Snowflake-Labs/snowflake-ai-kit/actions)
[![Plugin](https://img.shields.io/badge/Plugin-v3.6.0-green)](plugins/cortex-code)
[![Python](https://img.shields.io/badge/Python-3.9%2B-yellow)](https://python.org)

## Quick Start

### Claude Code

```bash
claude plugin install snowflake-cortex-code@claude-plugins-official
```

### OpenAI Codex

From your terminal:
```bash
codex plugin marketplace add Snowflake-Labs/snowflake-ai-kit
codex plugin add snowflake-cortex-code@snowflake-ai-kit
```

Or inside Codex, open `/plugins` and install "Snowflake Cortex Code" from the Snowflake AI Kit marketplace.

### Devin

Two plugins, depending on where Cortex Code runs:

- **Devin CLI, with the Cortex Code CLI installed on your machine:** the same Cortex Code plugin as Claude Code and Codex, with auto-routing and security envelopes. See [`plugins/cortex-code/`](plugins/cortex-code/README.md#devin-cli).

  ```bash
  devin plugins install Snowflake-Labs/snowflake-ai-kit#plugins/cortex-code --local
  ```

- **Devin Cloud, Desktop, or CLI, without the Cortex Code CLI:** the `snowflake-mcp-devin` plugin connects through a Snowflake Managed MCP Server, no Docker required. In Devin, go to Customize → Plugins → Add plugin → From repository, and enter this repo with subdirectory `plugins/snowflake-mcp-devin`. Or install from a clone:

  ```bash
  devin plugins install --local ./plugins/snowflake-mcp-devin
  ```

  Then connect with OAuth (custom MCP, signs in as you) or a role-restricted PAT on a service user. See the [Devin plugin README](plugins/snowflake-mcp-devin/README.md) for the Snowflake setup and both auth paths.

Use one or the other: with both installed, Devin may pick the MCP plugin's tools instead of routing to Cortex Code.

### That's it

Ask naturally — the plugin handles routing:

- "Show me my Snowflake warehouses"
- "What databases do I have access to?"
- "List all tables in my current schema"
- "Create a dynamic table that refreshes hourly"

Non-Snowflake prompts ("fix the bug in auth.py", "write a unit test") stay in your current agent.

## How It Works

```
You → Claude Code / Codex / Devin CLI → [Plugin detects Snowflake intent] → Cortex Code CLI → Snowflake
```

1. A lightweight keyword filter runs on every prompt (~50ms, no network)
2. If Snowflake intent is detected, the plugin routes to Cortex Code CLI
3. Cortex Code executes with 55+ specialized skills (SQL, governance, ML, streaming, etc.)
4. Results flow back to your agent session

To explicitly invoke Cortex Code (bypassing auto-detection):

```
$cortex-run show me my warehouses and their current state
```

In Devin CLI, use `/snowflake-cortex-code:cortex-run` instead.

> *See [`plugins/cortex-code/`](plugins/cortex-code/) for full documentation on security model, envelopes, and configuration.*

The Managed MCP Server plugin for Devin works differently. It has no hook and doesn't need the Cortex Code CLI. Devin calls a Snowflake Managed MCP Server over HTTPS, and a Cortex Code agent runs the task in a sandbox inside Snowflake:

```
Devin → [MCP over HTTPS] → Snowflake MCP server → Cortex Code agent → Snowflake
```

> *See the [Devin plugin README](plugins/snowflake-mcp-devin/README.md) for setup, auth, security, and troubleshooting.*

## Cursor

Works natively — enable "Third-party skills" in Cursor Settings. No separate plugin needed.

## Prerequisites

The plugin requires [Cortex Code CLI](https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-cli) (`cortex`) on your PATH. Install it from the [official docs](https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-cli).

It also needs Python 3.9 or later, and on Windows [Git Bash](https://git-scm.com/download/win), which its hooks run in.

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
| Devin CLI answers Snowflake prompts without Cortex Code | Run `devin plugins list`: `snowflake-cortex-code` must be installed, and the `snowflake` Managed MCP plugin removed (`devin plugins remove snowflake`). |
| Devin CLI: "A Snowflake MCP server is active" | Devin also loads MCP servers from Cursor, Windsurf, Claude Code, OpenCode, and Zed config. Run `devin mcp list` to find the server, then disable it or turn off that import with `read_config_from` in `~/.config/devin/config.json`. See [`plugins/cortex-code/`](plugins/cortex-code/README.md#devin-cli). |
| Devin CLI on Windows: `os error 1314` on install | Installing from a local folder creates a symlink. Turn on Developer Mode (Settings → System → For developers) and retry. |
| Installer hangs on Windows | Run PowerShell as Administrator. |

## Contributing

All PRs run CI on **macOS** and **Windows** via GitHub Actions ([`test.yml`](.github/workflows/test.yml)). The full test suite must pass on both platforms.

```bash
bash tests/run-tests.sh --verbose        # macOS / Linux
.\tests\run-tests.ps1 -Verbose           # Windows (PowerShell)
```

Optional live tests, which need the `cortex` CLI and a Snowflake connection:

```bash
bash tests/run-tests.sh --integration    # Cortex Code sessions against Snowflake
bash tests/run-tests.sh --devin-e2e      # Devin CLI routing to Cortex Code (also needs devin)
```

## License

Copyright (c) Snowflake Inc. All rights reserved.

Skills are licensed under the [Snowflake Skills License](LICENSE-SKILLS.md). All other content is [Apache 2.0](LICENSE).
