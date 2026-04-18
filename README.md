# Snowflake AI Kit

Developer tools for building on Snowflake with AI coding agents. One-command installer for Snowflake CLI + Cortex Code CLI, a Claude Code plugin with slash commands and automatic Snowflake routing (`/review`, `/rescue`, `/security-review`), and a sample Cortex Agent chat app (React + FastAPI).

## Table of Contents

- [Get Started](#get-started)
- [Usage](#usage)
- [Skills](#skills)
- [Plugins](#plugins)
- [Builder Apps](#builder-apps)
- [Troubleshooting](#troubleshooting)

## Get Started

The installer sets up Snowflake CLI and Cortex Code CLI. The [Cortex Code Plugin for Claude Code](#cortex-code-plugin-for-claude-code) is installed separately via the Claude Code marketplace.

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
claude /cortex-code:review     # Run a Cortex Code review from Claude Code
claude /cortex-code:rescue     # Hand off a stuck task to Cortex Code
```

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

Use Cortex Code from Claude Code. The plugin does two things:

1. **Auto-routing**: Snowflake-related prompts are automatically detected and routed to Cortex Code for execution (SQL queries, data governance, skill-based workflows).
2. **Slash commands**: Explicit commands like `/cortex-code:review`, `/cortex-code:rescue`, `/cortex-code:security-review` for on-demand Cortex Code workflows.

#### Install via Claude Code marketplace

No clone required. Run from your terminal:

```bash
# Add the Snowflake AI Kit as a Claude Code marketplace
claude plugin marketplace add https://github.com/Snowflake-Labs/snowflake-ai-kit

# Install the plugin
claude plugin install cortex-code@snowflake-ai-kit
```

To update later: `claude plugin update cortex-code`

Available commands:

| Command | Description |
|---|---|
| `/cortex-code:review` | Code review via Cortex Code |
| `/cortex-code:security-review` | Security-focused review |
| `/cortex-code:sql-review` | SQL review |
| `/cortex-code:dbt-review` | dbt project review |
| `/cortex-code:data-review` | Data pipeline review |
| `/cortex-code:adversarial-review` | Adversarial/red-team review |
| `/cortex-code:rescue` | Hand off a stuck task to Cortex Code |
| `/cortex-code:status` | Check Cortex Code availability |
| `/cortex-code:setup` | Configure the plugin |

> *See [`plugins/cortex-code/`](plugins/cortex-code/) for full documentation.*

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
