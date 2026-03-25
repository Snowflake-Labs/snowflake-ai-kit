# Snowflake AI Kit

Skills, MCP tools, and builder apps for AI coding agents working with Snowflake. Give your agent ([Cortex Code](https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-cli), Cursor, Windsurf, Claude Code, etc.) the patterns and best practices it needs to build on Snowflake correctly.

---

## What Can I Build?

- **Cortex Agents** — Multi-tool AI agents that orchestrate across Analyst, Search, and custom tools
- **AI Enrichment Pipelines** — Cortex AI Functions (classify, sentiment, summarize, extract) in pure SQL
- **RAG Search** — Cortex Search + AI_COMPLETE for retrieval-augmented generation over your docs
- **MCP Servers** — Expose Snowflake tools to any MCP-compatible AI client
- **ML Model Registry** — Train, register, and deploy models with `snowflake-ml-python`
- **Streamlit in Snowflake** — Deploy interactive apps with warehouse or container runtimes
- **Data Product Sharing** — Share data via secure shares, listings, and the Snowflake Marketplace
- **Declarative Data Pipelines** — Dynamic Tables with bronze/silver/gold medallion architecture
- **Open Table Format** — Iceberg tables with Snowflake-managed or external catalogs
- **Change Data Capture** — Streams and Tasks for incremental processing and task DAGs
- **Streaming Pipelines** — Snowpipe Streaming in Java or Python with exactly-once delivery
- **ETL Migrations** — SSIS-to-dbt replatforming on Snowflake
- **Snowflake Docs** — LLM-optimized documentation reference via `llms.txt` index
- **Docker Dev Environments** — Dockerfiles, Compose, Dev Containers for any stack
- **ORM Scaffolding** — Drizzle ORM with TypeScript schemas, migrations, and queries
- **Auth & Row-Level Security** — Supabase projects with RLS policies and auth integration
- ...and more as the community contributes

---

## Pick Your Path

| Path | Description |
|------|-------------|
| **Install Skills** | Add Snowflake skills to Cursor, Windsurf, Claude Code, Gemini CLI, or Cortex Code — [Quick Start](#install-skills) |
| **Browse Skills** | Explore available skills — [Snowflake](snowflake-skills/), [general-purpose](general-skills/), [Cortex Code skills](https://github.com/Snowflake-Labs/cortex-code-skills), or [bring your own](snowflake-skills/install_skills.sh) from external repos |
| **Claude Agent App** | Chat with Claude + Snowflake tools in one UI — [Setup Guide](builder-apps/claude-agent/) |
| **Cortex Agent App** | Chat with Cortex Agents, no API key needed — [Setup Guide](builder-apps/cortex-agent/) |

---

## Quick Start

### Install Skills

Add Snowflake skills to your existing AI coding agent.

**One-line install (Mac / Linux)**

```bash
bash <(curl -sSL https://raw.githubusercontent.com/Snowflake-Labs/snowflake-ai-kit/main/snowflake-skills/install_skills.sh)
```

This auto-detects your agent (Cursor, Windsurf, Claude Code, Gemini CLI) and installs all skills.

<details>
<summary><strong>Advanced options</strong></summary>

```bash
# Install for a specific agent
bash <(curl -sSL .../snowflake-skills/install_skills.sh) --agent cursor
bash <(curl -sSL .../snowflake-skills/install_skills.sh) --agent gemini

# Install specific skills only
bash <(curl -sSL .../snowflake-skills/install_skills.sh) docker-dev-setup drizzle-orm-setup

# Install skills from an external repo
bash <(curl -sSL .../snowflake-skills/install_skills.sh) --external https://raw.githubusercontent.com/org/repo/main skill-name

# List available skills
bash <(curl -sSL .../snowflake-skills/install_skills.sh) --list
```

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

## What's Included

| Component | Description |
|-----------|-------------|
| [`snowflake-skills/`](snowflake-skills/) | Snowflake-specific skills (Cortex Agents, AI Functions, RAG, MCP, ML Registry, Streamlit, Data Sharing, Dynamic Tables, Iceberg, Streams/Tasks, Snowpipe, ETL migration, Docs Reference) |
| [`general-skills/`](general-skills/) | General-purpose skills (Docker, Drizzle ORM, Supabase) |
| [`builder-apps/claude-agent/`](builder-apps/claude-agent/) | Claude Code agent UI with Snowflake MCP tools |
| [`builder-apps/cortex-agent/`](builder-apps/cortex-agent/) | Cortex Agent chat UI — no API key needed |

---

## Contributing

Want to add a skill? See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines, or use the [TEMPLATE](snowflake-skills/TEMPLATE/) to get started.

## License

Apache License 2.0. See [LICENSE](LICENSE) for details.
