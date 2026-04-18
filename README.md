# Snowflake AI Kit

Developer tools for building on Snowflake with AI coding agents. Includes a one-command installer for Snowflake CLI + Cortex Code CLI, a Claude Code plugin that automatically routes Snowflake prompts to Cortex Code, and a sample Cortex Agent chat app (React + FastAPI).

## Table of Contents

- [Get Started](#get-started)
- [Usage](#usage)
- [Skills](#skills)
- [Plugins](#plugins)
- [Builder Apps](#builder-apps)
- [Troubleshooting](#troubleshooting)

## Get Started

The installer sets up Snowflake CLI and Cortex Code CLI. The [Cortex Code plugin for Claude Code](#cortex-code-plugin-for-claude-code) is installed separately via the Claude Code marketplace -- it automatically detects Snowflake prompts and routes them to Cortex Code.

### What's Included

The installer sets up these components:

| Component | What it does | Install location |
|---|---|---|
| [Snowflake CLI](https://docs.snowflake.com/en/developer-guide/snowflake-cli/index) (`snow`) | Manage Snowflake objects, deploy apps, run SQL from the terminal | System PATH (via pipx/pip/brew) |
| [Cortex Code CLI](https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-cli) (`cortex`) | AI coding assistant for Snowflake — generate code, explore data, build apps | System PATH (via official installer) |

### Install

```bash
git clone https://github.com/Snowflake-Labs/snowflake-ai-kit.git
cd snowflake-ai-kit
```

#### Installer Options

| Flag | Description |
|---|---|
| `--check` / `-Check` | Check installation status without installing |
| `--update` / `-Update` | Re-install (overwrite existing) |
| `--help` / `-Help` | Show help |

#### macOS / Linux

```bash
bash install.sh
```

#### Windows (PowerShell)

```powershell
.\install.ps1
```

#### npx (any platform)

```bash
npx @snowflake-labs/ai-kit
```

### Snowflake Connection

Snow CLI and Cortex Code CLI both share the same Snowflake connection config (`~/.snowflake/connections.toml`). Set one up with:

```bash
snow connection add
```

## Usage

After installing, open a terminal and run:

```bash
cortex                         # Start Cortex Code (interactive AI assistant)
snow connection list           # Verify your Snowflake connection
cortex skill list              # Browse 35+ built-in skills
```

With the [plugin](#cortex-code-plugin-for-claude-code) installed, Claude Code automatically routes Snowflake prompts to Cortex Code:

```bash
claude                         # Start Claude Code — Snowflake queries auto-route to Cortex
```

Ask naturally ("show me my tables", "check data quality on SALES_DATA") and it routes to Cortex Code. Non-Snowflake prompts stay in Claude Code. See the [plugin docs](plugins/cortex-code/) for slash commands, security model, and configuration.

## Skills

### Bundled Skills (Cortex Code CLI)

Cortex Code CLI ships with 35+ built-in skills that activate automatically based on your prompt. No setup required -- they're included in every install.

View all available skills:

```bash
cortex skill list
```

Skills are organized by source:

| Category | Description |
|---|---|
| **BUNDLED** | Ship with the CLI binary. Updated automatically on `cortex update`. |
| **GLOBAL** | User-installed skills in `~/.snowflake/cortex/skills/`. Shared across all projects. |
| **EXTERNAL** | Added via `cortex skill add <path>`. Point to local directories or Git repos. |
| **PROJECT** | Discovered from the current working directory (e.g. `.claude/skills/`). |

Examples of bundled skills: `semantic-view`, `cortex-agent`, `data-quality`, `dynamic-tables`, `cost-intelligence`, `machine-learning`, `dashboard`, `iceberg`, `data-governance`, `cortex-ai-functions`, `deploy-to-spcs`, `lineage`.

Add a custom skill from a local path or GitHub:

```bash
cortex skill add /path/to/my-skill
cortex skill add owner/repo
```

## Plugins

### Cortex Code Plugin for Claude Code

Automatically route Snowflake work from Claude Code to Cortex Code. When you ask about your Snowflake data, the plugin detects the intent and delegates to Cortex Code -- no slash command needed. Just ask naturally:

- "Show me the top 10 customers by revenue"
- "Check data quality for the SALES_DATA table"
- "Create a dynamic table that refreshes hourly"

Non-Snowflake prompts ("fix the bug in auth.py", "write a unit test") stay in Claude Code as usual.

The plugin also includes slash commands for on-demand workflows: `/cortex-code:review`, `/cortex-code:rescue`, `/cortex-code:security-review`, and more.

#### Install via Claude Code marketplace

No clone required. Run from your terminal:

```bash
# Add the Snowflake AI Kit as a Claude Code marketplace
claude plugin marketplace add https://github.com/Snowflake-Labs/snowflake-ai-kit

# Install the plugin
claude plugin install cortex-code@snowflake-ai-kit
```

To update later: `claude plugin update cortex-code`

> *See [`plugins/cortex-code/`](plugins/cortex-code/) for full documentation, slash command reference, security model, and configuration.*

## Builder Apps

### Cortex Agent App

A sample React + FastAPI chat app built on the [Snowflake Cortex Agents REST API](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-agents-rest-api). Ask questions in natural language — the agent uses Cortex Analyst (text-to-SQL), Cortex Search (RAG), and data-to-chart to answer them. Runs entirely on Snowflake compute, no external API key needed.

*NOTE: Sample data included — setup.sql creates a demo agent with sales data, a semantic view, and a Cortex Search service.*

See [`builder-apps/cortex-agent/`](builder-apps/cortex-agent/) for setup and usage.

## Troubleshooting

| Problem | Fix |
|---|---|
| `snow: command not found` | Make sure `~/.local/bin` (pipx) or your Python scripts dir is in `$PATH`. Try opening a new terminal. |
| `cortex: command not found` | Re-run the installer. If it still fails, install manually from [ai.snowflake.com](https://ai.snowflake.com). |
| `pip`/`pipx` not found | Install Python 3.10+ first: [python.org](https://www.python.org/downloads/) |
| Connection errors | Run `snow connection add` to create `~/.snowflake/connections.toml`. Docs: [Specify credentials](https://docs.snowflake.com/en/developer-guide/snowflake-cli/connecting/specify-credentials) |
| Installer hangs on Windows | Run PowerShell as Administrator, or download and run the script manually. |
| Plugin not routing | Make sure the plugin is enabled: check `~/.claude/settings.json` has `"enabledPlugins": { "cortex-code@snowflake-ai-kit": true }` |

## License

Apache 2.0 — see [LICENSE](LICENSE).
