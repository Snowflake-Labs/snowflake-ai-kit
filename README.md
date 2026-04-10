# Snowflake AI Kit

Developer tools for building on Snowflake with AI coding agents. Includes a one-command installer for the Snowflake CLI and Cortex Code CLI, a sample Cortex Agent chat app (React + FastAPI), and agent-to-agent routing skills.

## Table of Contents

- [Get Started](#get-started)
- [Usage](#usage)
- [Skills](#skills)
- [Builder Apps](#builder-apps)
- [Troubleshooting](#troubleshooting)

## Get Started

The installer sets up Snowflake CLI and Cortex Code CLI by default, and optionally Claude Code CLI + Claude Code to Cortex Code router skill when you choose to include them. It skips anything already installed and verifies your Snowflake connection.

### What's Included

The installer sets up these components:

| Component | What it does | Install location |
|---|---|---|
| [Snowflake CLI](https://docs.snowflake.com/en/developer-guide/snowflake-cli/index) (`snow`) | Manage Snowflake objects, deploy apps, run SQL from the terminal | System PATH (via pipx/pip/brew) |
| [Cortex Code CLI](https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-cli) (`cortex`) | AI coding assistant for Snowflake — generate code, explore data, build apps | System PATH (via official installer) |
| [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) (`claude`) *(optional)* | AI coding agent by Anthropic | System PATH (via npm) |
| [Claude-to-Cortex Code Router](#claude-to-cortex-code-router) (Skill) *(optional)* | Route Snowflake operations from Claude Code to Cortex Code | `~/.claude/skills/cortex-code/` |

### Install

```bash
# Clone 
git clone https://github.com/Snowflake-Labs/snowflake-ai-kit.git
cd snowflake-ai-kit
```

Installer Options

| Flag | Description |
|---|---|
| `--check` / `-Check` | Check installation status without installing |
| `--update` / `-Update` | Re-install skills (overwrite existing) |
| `--with-claude` / `-WithClaude` | Also install Claude Code CLI and router skill (opt-in) |
| `--help` / `-Help` | Show help |

#### macOS / Linux

```bash
bash install.sh                  # default: Snow CLI + Cortex Code CLI
bash install.sh --with-claude    # also install Claude Code CLI + Cortex Code router skill
```

#### Windows (PowerShell)

```powershell
.\install.ps1                    # default: Snow CLI + Cortex Code CLI
.\install.ps1 -WithClaude        # also install Claude Code CLI + Cortex Code router skill
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

*NOTE: Installed by the installer when you opt in to Claude Code CLI (`--with-claude`).*

See [`agent-to-agent-skills/claude-cortex-code-router/`](agent-to-agent-skills/claude-cortex-code-router/) for setup and usage.

> **Credit:** Based on [sfc-gh-tjia/claude_skill_cortexcode](https://github.com/sfc-gh-tjia/claude_skill_cortexcode).

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
