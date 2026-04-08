# Snowflake AI Kit

Snowflake AI Toolkit for AI coding agents. Install the **Snowflake CLI** (`snow`), **Cortex Code CLI** (`cortex`), and **agent-to-agent skills** in one command.

## Table of Contents

- [Quick Install](#quick-install)
- [What's Included](#whats-included)
- [Skills](#skills)
- [Builder Apps](#builder-apps)
- [Repo Structure](#repo-structure)
- [Troubleshooting](#troubleshooting)

## Quick Install

### macOS / Linux

```bash
bash <(curl -sSL https://raw.githubusercontent.com/Snowflake-Labs/snowflake-ai-kit/main/install.sh)
```

### Windows (PowerShell)

```powershell
irm https://raw.githubusercontent.com/Snowflake-Labs/snowflake-ai-kit/main/install.ps1 | iex
```

### npx (any platform)

```bash
npx @snowflake-labs/ai-kit
```

The installer checks if each component is already installed and skips it if so. It also verifies your Snowflake connection configuration.

### Installer Options

| Flag | Description |
|---|---|
| `--check` / `-Check` | Check installation status without installing |
| `--update` / `-Update` | Re-install skills (overwrite existing) |
| `--help` / `-Help` | Show help |

## What's Included

The installer sets up three things:

| Component | What it does | Install location |
|---|---|---|
| [Snowflake CLI](https://docs.snowflake.com/en/developer-guide/snowflake-cli/index) (`snow`) | Manage Snowflake objects, deploy apps, run SQL from the terminal | System PATH (via pipx/pip/brew) |
| [Cortex Code CLI](https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-cli) (`cortex`) | AI coding assistant for Snowflake — generate code, explore data, build apps | System PATH (via official installer) |
| [Claude-to-Cortex Code Router](#claude-to-cortex-code-router) | Route Snowflake operations from Claude Code to Cortex Code | `~/.claude/skills/cortex-code/` |

Both CLIs share the same Snowflake connection config (`~/.snowflake/connections.toml`). Set one up with:

```bash
snow connection add
```

## Skills

### Claude-to-Cortex Code Router

Route Snowflake operations from [Claude Code](https://docs.anthropic.com/en/docs/claude-code) to [Cortex Code CLI](https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-cli) for specialized Snowflake expertise. Cortex Code has 30+ built-in skills (data quality, semantic views, cost intelligence, dynamic tables, ML pipelines, and more) that Claude Code can tap into through this skill.

Features: LLM-based semantic routing, security envelopes (RO/RW/RESEARCH/DEPLOY), approval modes, PII sanitization, audit logging, and a full test suite.

See [`agent-to-agent-skills/claude-cortex-code-router/`](agent-to-agent-skills/claude-cortex-code-router/) for setup and usage.

> **Credit:** Based on [sfc-gh-tjia/claude_skill_cortexcode](https://github.com/sfc-gh-tjia/claude_skill_cortexcode).

## Builder Apps

### Cortex Agent App

A chat UI for [Snowflake Cortex Agents](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-agents). Ask questions in natural language — the agent uses Cortex Analyst (text-to-SQL), Cortex Search (RAG), and custom tools to answer them. Runs entirely on Snowflake compute, no external API key needed.

See [`builder-apps/cortex-agent/`](builder-apps/cortex-agent/) for setup and usage.

## Repo Structure

```
snowflake-ai-kit/
├── install.sh              # CLI + skills installer (macOS/Linux)
├── install.ps1             # CLI + skills installer (Windows)
├── bin/install.mjs         # npx entry point
├── agent-to-agent-skills/
│   └── claude-cortex-code-router/  # Route Claude Code → Cortex Code
├── builder-apps/
│   └── cortex-agent/       # Cortex Agent chat UI (React + FastAPI)
├── package.json
├── LICENSE
├── SECURITY.md
└── VERSION
```

## Troubleshooting

| Problem | Fix |
|---|---|
| `snow: command not found` | Make sure `~/.local/bin` (pipx) or your Python scripts dir is in `$PATH`. Try opening a new terminal. |
| `cortex: command not found` | Re-run the installer. If it still fails, install manually from [ai.snowflake.com](https://ai.snowflake.com). |
| `pip`/`pipx` not found | Install Python 3.10+ first: [python.org](https://www.python.org/downloads/) |
| Connection errors | Run `snow connection add` to create `~/.snowflake/connections.toml`. Docs: [Specify credentials](https://docs.snowflake.com/en/developer-guide/snowflake-cli/connecting/specify-credentials) |
| Installer hangs on Windows | Run PowerShell as Administrator, or download and run the script manually. |
| Skill install fails | The repo is internal — you need SSH access to Snowflake-Labs. Try: `git clone git@github.com:Snowflake-Labs/snowflake-ai-kit.git` manually. |
| Skill already installed | Run with `--update` to overwrite: `bash <(curl -sSL .../install.sh) --update` |

## License

Apache 2.0 — see [LICENSE](LICENSE).
