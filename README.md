# Snowflake AI Kit

Skills, MCP tools, and builder apps for AI coding agents working with Snowflake. Give your agent (Cortex Code, Cursor, Windsurf, Claude Code, Gemini CLI, etc.) the patterns and best practices it needs to build on Snowflake correctly.

### Table of Contents

- [What Can I Build?](#what-can-i-build)
- [Pick Your Path](#pick-your-path)
- [Quick Start](#quick-start)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

---

## What Can I Build?

**AI & Agents**
- Cortex Agents — Multi-tool AI agents that orchestrate across Analyst, Search, and custom tools
- AI Enrichment Pipelines — Cortex AI Functions (classify, sentiment, summarize, extract) in pure SQL
- RAG Search — Cortex Search + AI_COMPLETE for retrieval-augmented generation over your docs
- MCP Servers — Expose Snowflake tools to any MCP-compatible AI client
- [Claude-to-Cortex Code Router](agent-to-agent-skills/claude-cortex-code-router/) — Route Snowflake tasks from Claude Code to Cortex Code for specialized expertise

**Data & ML**
- ML Model Registry — Train, register, and deploy models with `snowflake-ml-python`
- Declarative Data Pipelines — Dynamic Tables with bronze/silver/gold medallion architecture
- Change Data Capture — Streams and Tasks for incremental processing and task DAGs
- Streaming Pipelines — Snowpipe Streaming in Java or Python with exactly-once delivery
- Snowflake Postgres — Create and manage fully managed Postgres instances on Snowflake

**Apps & Sharing**
- Streamlit in Snowflake — Deploy interactive apps with warehouse or container runtimes
- Data Product Sharing — Share data via secure shares, listings, and the Snowflake Marketplace

**Storage & Migration**
- Open Table Format — Iceberg tables with Snowflake-managed or external catalogs
- ETL Migrations — SSIS-to-dbt replatforming on Snowflake

**General Purpose**
- Docker Dev Environments — Dockerfiles, Compose, Dev Containers for any stack
- ORM Scaffolding — Drizzle ORM with TypeScript schemas, migrations, and queries
- Auth & Row-Level Security — Supabase projects with RLS policies and auth integration

**Reference**
- Snowflake Docs — LLM-optimized documentation reference via `llms.txt` index

...and more as the community contributes

---

## Pick Your Path

| Path | Description |
|------|-------------|
| **Install Skills** | Add Snowflake skills to Cursor, Windsurf, Claude Code, Gemini CLI, or Cortex Code — [Quick Start](#quick-start) |
| **Browse Skills** | Explore available skills — [Snowflake](snowflake-skills/), [agent-to-agent](agent-to-agent-skills/), [general-purpose](general-skills/), [Cortex Code skills](https://github.com/Snowflake-Labs/cortex-code-skills), or [bring your own](snowflake-skills/install_skills.sh) from external repos |
| **Claude Agent App** | Chat with Claude + Snowflake tools in one UI — [Setup Guide](builder-apps/claude-agent/) |
| **Cortex Agent App** | Chat with Cortex Agents, no API key needed — [Setup Guide](builder-apps/cortex-agent/) |

---

## Quick Start

### One-Line Install (Mac / Linux)

```bash
bash <(curl -sSL https://raw.githubusercontent.com/Snowflake-Labs/snowflake-ai-kit/main/install.sh)
```

### One-Line Install (Windows PowerShell)

```powershell
irm https://raw.githubusercontent.com/Snowflake-Labs/snowflake-ai-kit/main/install.ps1 | iex
```

The installer automatically sets up [**Snowflake CLI**](https://docs.snowflake.com/en/developer-guide/snowflake-cli/installation/installation) (`snow`) and [**Cortex Code CLI**](https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-cli) (`cortex`) if not already installed, then lets you choose: skills only, skills + a builder app, or everything.

<details>
<summary><strong>Non-interactive options</strong></summary>

```bash
# Skills only — auto-detects your agent
bash <(curl -sSL .../install.sh) --skills-only

# Skills + Cortex Agent app (no external API key needed)
bash <(curl -sSL .../install.sh) --app cortex-agent

# Skills + Claude Agent app (needs Anthropic API key)
bash <(curl -sSL .../install.sh) --app claude-agent

# Everything — skills + all builder apps
bash <(curl -sSL .../install.sh) --all

# Install for a specific agent
bash <(curl -sSL .../install.sh) --skills-only --agent cursor

# List available skills
bash <(curl -sSL .../install.sh) --list
```

</details>

<details>
<summary><strong>Skills-only install</strong></summary>

If you only want skills (no builder apps), you can also use the skills installer directly:

```bash
bash <(curl -sSL https://raw.githubusercontent.com/Snowflake-Labs/snowflake-ai-kit/main/snowflake-skills/install_skills.sh)
```

This auto-detects your agent (Cursor, Windsurf, Claude Code, Gemini CLI) and installs all skills.

</details>

<details>
<summary><strong>Manual install</strong></summary>

Clone the repo and copy skills into your agent's rules directory:

```bash
git clone https://github.com/Snowflake-Labs/snowflake-ai-kit.git
```

**Cursor**
```bash
cp snowflake-ai-kit/snowflake-skills/docker-dev-setup/SKILL.md .cursor/rules/docker-dev-setup.mdc
```

**Windsurf**
```bash
cp snowflake-ai-kit/snowflake-skills/docker-dev-setup/SKILL.md .windsurf/rules/docker-dev-setup.md
```

**Claude Code**
```bash
cp snowflake-ai-kit/snowflake-skills/docker-dev-setup/SKILL.md .claude/rules/docker-dev-setup.md
```

**Gemini CLI**
```bash
cp snowflake-ai-kit/snowflake-skills/docker-dev-setup/SKILL.md .gemini/docker-dev-setup.md
```

**Cortex Code** — Add to `~/.snowflake/cortex/skills.json`:
```json
{
  "remote": [
    {
      "source": "https://github.com/Snowflake-Labs/snowflake-ai-kit",
      "ref": "main",
      "skills": [
        { "name": "docker-dev-setup" },
        { "name": "drizzle-orm-setup" },
        { "name": "supabase-auth-rls" }
      ]
    }
  ]
}
```

**Other Agents (Cline, Aider, etc.)** — Point the agent at the `SKILL.md` file directly, or paste its contents into the agent's system prompt.

</details>

<details>
<summary><strong>External skills</strong></summary>

Pull skills from any GitHub repo that follows the `skill-name/SKILL.md` convention:

```bash
# Install Cortex Code bundled skills
bash <(curl -sSL .../snowflake-skills/install_skills.sh) \
  --external https://raw.githubusercontent.com/Snowflake-Labs/cortex-code-skills/main/skills \
  semantic-view cortex-agent data-quality

# Install from any repo
bash <(curl -sSL .../snowflake-skills/install_skills.sh) \
  --external https://raw.githubusercontent.com/org/repo/main/skills-dir \
  skill-a skill-b

# Mix built-in and external skills
bash <(curl -sSL .../snowflake-skills/install_skills.sh) \
  cortex-agents \
  --external https://raw.githubusercontent.com/Snowflake-Labs/cortex-code-skills/main/skills \
  dynamic-tables
```

The `--external` flag takes a base URL followed by one or more skill names. The installer fetches `<URL>/<skill>/SKILL.md` for each and installs it the same way as built-in skills.

**Repo structure expected:**

```
your-repo/
├── skill-a/
│   └── SKILL.md
└── skill-b/
    └── SKILL.md
```

</details>

### Claude Agent App

Chat with Claude + Snowflake MCP tools in a single UI.

> **Tip:** `bash <(curl -sSL .../install.sh) --app claude-agent` handles the full setup.

**Prerequisites:**
- Snowflake account (PAT or password auth)
- [Anthropic API key](https://console.anthropic.com/)
- Python 3.11+
- Node.js 18+

```bash
git clone https://github.com/Snowflake-Labs/snowflake-ai-kit.git
cd snowflake-ai-kit/builder-apps/claude-agent
./scripts/setup.sh
# Follow instructions to start the app
```

See [`builder-apps/claude-agent/`](builder-apps/claude-agent/) for details.

### Cortex Agent App

Chat with Snowflake Cortex Agents — no external API key needed.

> **Tip:** `bash <(curl -sSL .../install.sh) --app cortex-agent` handles the full setup.

**Prerequisites:**
- Snowflake account with a [Cortex Agent](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-agents) created
- Python 3.11+
- Node.js 18+

```bash
git clone https://github.com/Snowflake-Labs/snowflake-ai-kit.git
cd snowflake-ai-kit/builder-apps/cortex-agent
./scripts/setup.sh
# Follow instructions to start the app
```

See [`builder-apps/cortex-agent/`](builder-apps/cortex-agent/) for details.

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `snow: command not found` after install | PATH not refreshed | Restart your terminal, or run `source ~/.bashrc` / `source ~/.zshrc` |
| `cortex: command not found` after install | PATH not refreshed | Restart your terminal, or add `~/.local/bin` to your PATH |
| `pipx: command not found` | pipx not installed | `pip install pipx` or `brew install pipx`, then rerun the installer |
| Snowflake CLI install fails entirely | No pip, pipx, or brew available | Install [Python 3.10+](https://www.python.org/downloads/) first, then rerun |
| `snow connection add` — not sure what to enter | First time connecting | You need your **account identifier** (e.g. `xy12345.us-east-1`), **username**, and **auth method** (password or [PAT](https://docs.snowflake.com/en/user-guide/programmatic-access-tokens)). See [connection docs](https://docs.snowflake.com/en/developer-guide/snowflake-cli/connecting/specify-credentials) |
| `connections.toml` exists but auth fails | Wrong credentials or expired token | Run `snow connection test` to diagnose, then update `~/.snowflake/connections.toml` |
| PowerShell script won't run (Windows) | Execution policy blocks scripts | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` then retry |
| `npm install` fails in builder app | Node.js too old or network issue | Check `node --version` (need 18+), check your network/proxy |
| `pip install` fails in builder app | Python too old or permissions | Check `python3 --version` (need 3.11+), try `pip install --user` or use a venv |
| Skills installed but agent doesn't see them | Agent hasn't reloaded rules | Restart your IDE or agent, and verify the rules folder exists (e.g. `.cursor/rules/`) |

---

## Contributing

Want to add a skill? See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines, or use the [TEMPLATE](snowflake-skills/TEMPLATE/) to get started.

## License

Apache License 2.0. See [LICENSE](LICENSE) for details.
