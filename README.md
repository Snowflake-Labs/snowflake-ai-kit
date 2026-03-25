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

| Adventure | Best For | Start Here |
|-----------|----------|------------|
| **Install Skills** | Add Snowflake skills to your agents | [Install](#install-skills) |
| **Browse Skills** | Explore patterns and best practices | [`snowflake-skills/`](snowflake-skills/) |
| **Claude Agent App** | Chat with Claude + Snowflake tools in one UI | [`builder-apps/claude-agent/`](builder-apps/claude-agent/) |
| **Cortex Agent App** | Chat with Cortex Agents — no API key needed | [`builder-apps/cortex-agent/`](builder-apps/cortex-agent/) |

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
