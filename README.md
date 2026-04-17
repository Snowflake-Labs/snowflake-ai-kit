# Snowflake AI Kit

Developer tools for building on Snowflake with AI coding agents. One-command installer for Snowflake CLI + Cortex Code CLI, a Claude Code plugin with slash commands (`/review`, `/rescue`, `/security-review`), an agent-to-agent routing skill, and a sample Cortex Agent chat app (React + FastAPI).

## Table of Contents

- [Get Started](#get-started)
- [Usage](#usage)
- [Skills](#skills)
- [Plugins](#plugins)
 - [Cortex Code Router Skill vs Cortex Code Plugin for Claude](#cortex-code-router-skill-vs-cortex-code-plugin-for-claude)
- [Multi-Agent Integrations](#multi-agent-integrations)
- [Builder Apps](#builder-apps)
- [Troubleshooting](#troubleshooting)

## Get Started

The installer sets up Snowflake CLI and Cortex Code CLI by default. Optionally add Claude Code CLI with the agent-to-agent router skill (`--with-claude`). The [Cortex Code Plugin for Claude Code](#cortex-code-plugin-for-claude-code) is installed separately via the Claude Code marketplace.

### What's Included

The installer sets up these components:

| Component | What it does | Install location |
|---|---|---|
| [Snowflake CLI](https://docs.snowflake.com/en/developer-guide/snowflake-cli/index) (`snow`) | Manage Snowflake objects, deploy apps, run SQL from the terminal | System PATH (via pipx/pip/brew) |
| [Cortex Code CLI](https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-cli) (`cortex`) | AI coding assistant for Snowflake — generate code, explore data, build apps | System PATH (via official installer) |
| [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) (`claude`) *(optional)* | AI coding agent by Anthropic | System PATH (via npm) |
| [Claude Code to Cortex Code Router Skill](#claude-code-to-cortex-code-router-skill) *(optional)* | Route Snowflake operations from Claude Code to Cortex Code | `~/.claude/skills/cortex-code/` |
| [Cursor integration](#cursor) *(optional)* | Cortex Code skill + auto-routing rule for Cursor | `~/.cursor/skills-cursor/cortex-code/` |
| [Codex integration](#codex) *(optional)* | Standalone CLI tool for OpenAI Codex agent | `~/.local/bin/cortexcode-tool` |

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
| `--with-cursor` / `-WithCursor` | Install Cortex Code skill + routing rule for Cursor |
| `--with-codex` / `-WithCodex` | Install cortexcode-tool CLI for Codex |
| `--with-all` / `-WithAll` | Install integrations for all supported agents |
| `--help` / `-Help` | Show help |

#### macOS / Linux

```bash
bash install.sh                  # default: Snow CLI + Cortex Code CLI
bash install.sh --with-claude    # also install Claude Code CLI + Cortex Code router skill
bash install.sh --with-all       # install all agent integrations
```

#### Windows (PowerShell)

```powershell
.\install.ps1                    # default: Snow CLI + Cortex Code CLI
.\install.ps1 -WithClaude        # also install Claude Code CLI + Cortex Code router skill
.\install.ps1 -WithAll           # install all agent integrations
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

For Claude Code users with the [plugin](#cortex-code-plugin-for-claude-code) installed:

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

### Claude Code to Cortex Code Router Skill

Route Snowflake operations from [Claude Code](https://docs.anthropic.com/en/docs/claude-code) to [Cortex Code CLI](https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-cli) for specialized Snowflake expertise. When Claude Code gets a Snowflake-related prompt, this skill routes it to Cortex Code where the bundled skills above handle the work.

Features: LLM-based semantic routing, security envelopes (RO/RW/RESEARCH/DEPLOY), approval modes, PII sanitization, audit logging, and a full test suite.

> *Installed by the installer when you opt in to Claude Code CLI (`--with-claude`). See [`agent-to-agent-skills/claude-cortex-code-router/`](agent-to-agent-skills/claude-cortex-code-router/) for manual setup and full documentation.*

## Plugins

### Cortex Code Plugin for Claude Code

Use Cortex Code directly from Claude Code via slash commands. The plugin registers commands like `/cortex-code:review`, `/cortex-code:rescue`, `/cortex-code:security-review`, and more through the Claude Code plugin marketplace.

#### Install via Claude Code marketplace

No clone required. Run from your terminal:

```bash
# Add the Snowflake AI Kit as a Claude Code marketplace
claude plugin marketplace add https://github.com/Snowflake-Labs/snowflake-ai-kit

# Install the plugin
claude plugin install cortex-code-plugin@snowflake-ai-kit
```

To update later: `claude plugin update cortex-code-plugin`

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

## Cortex Code Router Skill vs Cortex Code Plugin for Claude

Both work with [Claude Code](https://docs.anthropic.com/en/docs/claude-code). They solve different problems and can be installed together.

| | Router Skill | Plugin |
|---|---|---|
| **How it works** | Auto-routes Snowflake prompts from Claude Code to Cortex Code transparently | Explicit slash commands (`/cortex-code:review`, etc.) you invoke manually in Claude Code |
| **Best for** | "I want Claude Code to automatically use Cortex Code for Snowflake tasks" | "I want specific Cortex Code workflows on demand (code review, rescue, security audit)" |
| **Install** | `bash install.sh --with-claude` | `claude plugin install cortex-code-plugin@snowflake-ai-kit` ([details](#cortex-code-plugin-for-claude-code)) |
| **Conflict?** | No -- install both if you want automatic routing AND explicit commands | No -- install both |

## Multi-Agent Integrations

Cortex Code can be used as a backend for multiple AI coding agents. Each integration routes Snowflake operations from the host agent to Cortex Code CLI, giving the agent access to 35+ bundled Snowflake skills.

| Agent | Integration type | Install flag | Details |
|---|---|---|---|
| **Claude Code** | Skill-based (SKILL.md) | `--with-claude` | [Router skill](#claude-code-to-cortex-code-router-skill) |
| **Cursor** | Skill + `.mdc` routing rule | `--with-cursor` | [Setup](#cursor) |
| **Windsurf** | Skill-based (Cascade auto-discovers) | `--with-claude` | Same skill as Claude Code — Cascade reads `~/.claude/skills/` |
| **Codex** | Standalone CLI (`cortexcode-tool`) | `--with-codex` | [Setup](#codex) |
| **VSCode / Terminal** | Standalone CLI (`cortexcode-tool`) | `--with-codex` | Same CLI tool, run directly |

All integrations share the same core skill at `agent-to-agent-skills/claude-cortex-code-router/` — no code duplication across agents.

### Cursor

Installs the Cortex Code skill into Cursor's skill directory and adds an auto-routing rule (`.mdc`) that detects Snowflake-related prompts.

```bash
bash install.sh --with-cursor
# or standalone:
bash integrations/cursor/install.sh
```

After install, restart Cursor. The routing rule (`cortex-snowflake-routing.mdc`) activates automatically for prompts containing Snowflake keywords.

To uninstall: `bash integrations/cursor/uninstall.sh`

See [`integrations/cursor/`](integrations/cursor/) for details.

### Codex

Installs `cortexcode-tool`, a standalone Python CLI that wraps `cortex` for non-TTY environments like OpenAI Codex. Uses `--bypass` mode and streams JSON output.

```bash
bash install.sh --with-codex
# or standalone:
bash integrations/codex/install.sh
```

The Codex config (`cortexcode-tool-codex.yaml`) uses `~/.cache/` paths to work within Codex's sandbox. The tool auto-detects your Snowflake connection from `~/.snowflake/connections.toml`.

To uninstall: `bash integrations/codex/uninstall.sh`

See [`integrations/codex/`](integrations/codex/) for details.

### Windsurf

No separate integration needed. Windsurf's Cascade agent auto-discovers skills from `~/.claude/skills/`. Install the Claude Code router skill (`--with-claude`) and Windsurf picks it up automatically.

### Security Model

All integrations support configurable security envelopes:

| Envelope | Allowed operations |
|---|---|
| **RO** (read-only) | SELECT, DESCRIBE, SHOW, list operations |
| **RW** (read-write) | RO + INSERT, UPDATE, DELETE, CREATE, ALTER |
| **RESEARCH** | RO + web search, documentation lookups |
| **DEPLOY** | RW + deployment operations (CREATE APPLICATION, etc.) |

Approval modes: `auto` (no prompts), `prompt` (ask before executing), `strict` (require explicit approval for each operation). Configure per-agent in the integration's config file.

See [`integrations/README.md`](integrations/README.md) for the full architecture overview.

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
| Cursor skill not detected | Restart Cursor after install. Check `~/.cursor/skills-cursor/cortex-code/SKILL.md` exists. |
| `cortexcode-tool: command not found` | Ensure `~/.local/bin` is in `$PATH`. Re-run: `bash integrations/codex/install.sh` |

## License

Apache 2.0 — see [LICENSE](LICENSE).
