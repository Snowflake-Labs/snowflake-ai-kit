# Snowflake AI Kit

Connect your AI coding agent to Snowflake. Plugins for **Claude Code** and **OpenAI Codex** that automatically detect Snowflake prompts and route them to a **CoCo Cloud Agent** — where 55+ built-in skills handle SQL, data governance, dynamic tables, ML, and more.

[![Claude Code](https://img.shields.io/badge/Claude%20Code-Marketplace-8A2BE2)](https://claude.com/plugins/snowflake-cortex-code)
[![OpenAI Codex](https://img.shields.io/badge/OpenAI%20Codex-Marketplace-orange)](https://github.com/Snowflake-Labs/snowflake-ai-kit#openai-codex)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue)](LICENSE)
[![CI](https://img.shields.io/github/actions/workflow/status/Snowflake-Labs/snowflake-ai-kit/test.yml?label=CI)](https://github.com/Snowflake-Labs/snowflake-ai-kit/actions)
[![Plugin](https://img.shields.io/badge/Plugin-v3.3.0-green)](plugins/cortex-code)
[![Python](https://img.shields.io/badge/Python-3.12%2B-yellow)](https://python.org)

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

### That's it

Ask naturally — the plugin handles routing:

- "Show me my Snowflake warehouses"
- "What databases do I have access to?"
- "List all tables in my current schema"
- "Create a dynamic table that refreshes hourly"

Non-Snowflake prompts ("fix the bug in auth.py", "write a unit test") stay in your current agent.

## How It Works

```
You → Claude Code / Codex → [Plugin detects Snowflake intent] → Cloud Agent → Snowflake
```

1. A lightweight keyword filter runs on every prompt (~50ms, no network)
2. If Snowflake intent is detected, the plugin spawns a CoCo Cloud Agent
3. The Cloud Agent executes in a remote sandbox with 55+ specialized skills (SQL, governance, ML, streaming, etc.)
4. Results flow back to your agent session

No local CLI required — the Cloud Agent runs remotely with full Snowflake access.

To explicitly invoke Cortex Code (bypassing auto-detection):

```
$cortex-run show me my warehouses and their current state
```

> *See [`plugins/cortex-code/`](plugins/cortex-code/) for full documentation on security model, envelopes, and configuration.*

## Cursor

Works natively — enable "Third-party skills" in Cursor Settings. No separate plugin needed.

## Authentication

The plugin authenticates to Snowflake via browser SSO on first use. No credentials to manage manually.

### Snowflake Connection

For local CLI fallback, configure a connection at `~/.snowflake/connections.toml`:

```bash
snow connection add
```

## Cloud Agents MCP Server

The [`mcp-servers/cloud-agents/`](mcp-servers/cloud-agents/) directory contains a standalone MCP server that any MCP-compatible client can use to spawn CoCo Cloud Agents. See [TESTING.md](mcp-servers/cloud-agents/TESTING.md) for setup instructions.

## Installer

The bundled installer sets up Snowflake CLI (`snow`) and optionally Cortex Code CLI (`cortex`) for local fallback:

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

The Cloud Agent has 55+ built-in skills that activate automatically based on your prompt:

Examples: `semantic-view`, `cortex-agent`, `data-quality`, `dynamic-tables`, `cost-intelligence`, `machine-learning`, `iceberg`, `data-governance`, `cortex-ai-functions`, `deploy-to-spcs`, `lineage`, `dbt-projects-on-snowflake`, `snowflake-notebooks`, `security-investigation`, `workload-performance-analysis`.

## Troubleshooting

| Problem | Fix |
|---|---|
| Auth expired mid-session | Restart session — browser SSO will re-authenticate |
| Plugin not routing | Verify plugin is enabled in your agent's settings |
| Slow first response | Expected: ~10-20s (cloud agent sandbox boot + execution) |
| Connection errors | Run `snow connection add`. Docs: [Specify credentials](https://docs.snowflake.com/en/developer-guide/snowflake-cli/connecting/specify-credentials) |
| Installer hangs on Windows | Run PowerShell as Administrator |

## Contributing

All PRs run CI on **macOS** and **Windows** via GitHub Actions ([`test.yml`](.github/workflows/test.yml)). The full test suite (200 tests) must pass on both platforms.

```bash
bash tests/run-tests.sh --verbose        # macOS / Linux
.\tests\run-tests.ps1 -Verbose           # Windows (PowerShell)
```

## License

Copyright (c) Snowflake Inc. All rights reserved.

Skills are licensed under the [Snowflake Skills License](LICENSE-SKILLS.md). All other content is [Apache 2.0](LICENSE).
