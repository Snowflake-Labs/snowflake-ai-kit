# Snowflake AI Kit

Developer tools for building on Snowflake with AI coding agents. One-command installer for Snowflake CLI + Cortex Code CLI, a Claude Code plugin with slash commands (`/review`, `/rescue`, `/security-review`), an agent-to-agent routing skill, and a sample Cortex Agent chat app (React + FastAPI).

## Table of Contents

- [Get Started](#get-started)
- [Usage](#usage)
- [Skills](#skills)
- [Plugins (Claude Code)](#plugins-claude-code)
- [Builder Apps](#builder-apps)
- [Troubleshooting](#troubleshooting)

## Get Started

The installer sets up Snowflake CLI and Cortex Code CLI by default. Optionally add Claude Code CLI with the agent-to-agent router skill (`--with-claude`) or the full Cortex Code Plugin for Claude Code (`--with-plugin`). It skips anything already installed and verifies your Snowflake connection.

### What's Included

The installer sets up these components:

| Component | What it does | Install location |
|---|---|---|
| [Snowflake CLI](https://docs.snowflake.com/en/developer-guide/snowflake-cli/index) (`snow`) | Manage Snowflake objects, deploy apps, run SQL from the terminal | System PATH (via pipx/pip/brew) |
| [Cortex Code CLI](https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-cli) (`cortex`) | AI coding assistant for Snowflake — generate code, explore data, build apps | System PATH (via official installer) |
| [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) (`claude`) *(optional)* | AI coding agent by Anthropic | System PATH (via npm) |
| [Claude-to-Cortex Code Router](#claude-to-cortex-code-router) (Skill) *(optional)* | Route Snowflake operations from Claude Code to Cortex Code | `~/.claude/skills/cortex-code/` |
| [Cortex Code Plugin](#cortex-code-plugin-for-claude-code) *(optional)* | Slash commands (`/review`, `/rescue`, etc.) for Claude Code via the plugin system | Registered via `/plugins add` |

### Install

```bash
git clone https://github.com/Snowflake-Labs/snowflake-ai-kit.git
cd snowflake-ai-kit
```

#### Installer Options

| Flag | Description |
|---|---|
| `--check` / `-Check` | Check installation status without installing |
| `--update` / `-Update` | Re-install skills (overwrite existing) |
| `--with-claude` / `-WithClaude` | Also install Claude Code CLI and router skill (opt-in) |
| `--with-plugin` / `-WithPlugin` | Also install Cortex Code Plugin for Claude Code (implies `--with-claude`) |
| `--help` / `-Help` | Show help |

#### macOS / Linux

```bash
bash install.sh                  # default: Snow CLI + Cortex Code CLI
bash install.sh --with-claude    # also install Claude Code CLI + Cortex Code router skill
bash install.sh --with-plugin    # all of the above + Cortex Code Plugin for Claude Code
```

#### Windows (PowerShell)

```powershell
.\install.ps1                    # default: Snow CLI + Cortex Code CLI
.\install.ps1 -WithClaude        # also install Claude Code CLI + Cortex Code router skill
.\install.ps1 -WithPlugin        # all of the above + Cortex Code Plugin for Claude Code
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

For Claude Code users (if installed with `--with-claude`):

```bash
claude                         # Start Claude Code with Cortex Code routing
```

For Claude Code users with the plugin (if installed with `--with-plugin`):

```bash
claude /cortex-code:review     # Run a Cortex Code review from Claude Code
claude /cortex-code:rescue     # Hand off a stuck task to Cortex Code
claude /cortex-code:status     # Check Cortex Code availability
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

### Claude-to-Cortex Code Router

Route Snowflake operations from [Claude Code](https://docs.anthropic.com/en/docs/claude-code) to [Cortex Code CLI](https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-cli) for specialized Snowflake expertise. When Claude Code gets a Snowflake-related prompt, this skill routes it to Cortex Code where the bundled skills above handle the work.

Features: LLM-based semantic routing, security envelopes (RO/RW/RESEARCH/DEPLOY), approval modes, PII sanitization, audit logging, and a full test suite.

> *Installed by the installer when you opt in to Claude Code CLI (`--with-claude`). See [`agent-to-agent-skills/claude-cortex-code-router/`](agent-to-agent-skills/claude-cortex-code-router/) for manual setup and full documentation.*

## Plugins (Claude Code)

Both the Router Skill and the Plugin work with [Claude Code](https://docs.anthropic.com/en/docs/claude-code). They solve different problems and can be installed together.

| | Router Skill (`--with-claude`) | Plugin (`--with-plugin`) |
|---|---|---|
| **How it works** | Auto-routes Snowflake prompts from Claude Code to Cortex Code transparently | Explicit slash commands (`/cortex-code:review`, etc.) you invoke manually in Claude Code |
| **Best for** | "I want Claude Code to automatically use Cortex Code for Snowflake tasks" | "I want specific Cortex Code workflows on demand (code review, rescue, security audit)" |
| **Requires** | Claude Code CLI | Claude Code CLI |
| **Conflict?** | No -- install both if you want automatic routing AND explicit commands | No -- install both |

### Cortex Code Plugin for Claude Code

Use Cortex Code directly from Claude Code via slash commands. The plugin registers commands like `/cortex-code:review`, `/cortex-code:rescue`, `/cortex-code:security-review`, and more through the Claude Code plugin system.

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

> *Installed by the installer when you opt in to the plugin (`--with-plugin`). See [`plugins/cortex-code/`](plugins/cortex-code/) for manual setup and full documentation.*

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
| `claude: command not found` | Requires Node.js + npm. Install Node.js from [nodejs.org](https://nodejs.org), then: `npm install -g @anthropic-ai/claude-code` |
| `pip`/`pipx` not found | Install Python 3.10+ first: [python.org](https://www.python.org/downloads/) |
| Connection errors | Run `snow connection add` to create `~/.snowflake/connections.toml`. Docs: [Specify credentials](https://docs.snowflake.com/en/developer-guide/snowflake-cli/connecting/specify-credentials) |
| Installer hangs on Windows | Run PowerShell as Administrator, or download and run the script manually. |
| Skill install fails | The repo is internal — you need access to Snowflake-Labs. Try: `git clone https://github.com/Snowflake-Labs/snowflake-ai-kit.git` manually. |
| Skill already installed | Run with `--update` to overwrite: `bash <(curl -sSL .../install.sh) --update` |

## License

Apache 2.0 — see [LICENSE](LICENSE).
