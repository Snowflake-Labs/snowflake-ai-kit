# Cortex Agents

Create AI agents that orchestrate across structured and unstructured data — routing questions to Cortex Analyst, Cortex Search, and custom tools automatically.

## What It Does

This skill guides your AI coding agent through building a Cortex Agent:

1. **Setup** — Create sample data, a semantic view, and a search service
2. **Create** — Define the agent with `CREATE AGENT ... FROM SPECIFICATION`
3. **Test** — Invoke the agent via REST API or SQL
4. **Extend** — Add custom tools (UDFs/stored procedures)

## Prerequisites

- Snowflake account with Cortex Agents enabled
- `CREATE AGENT` privilege on the target schema
- `SNOWFLAKE.CORTEX_USER` database role
- Semantic view and/or Cortex Search Service (created during setup)

## Quick Start

Ask your AI coding agent:

> "Create a Cortex Agent that can answer questions about my sales data and company policies"

Or for a demo:

> "Build a demo Cortex Agent with Analyst and Search tools"

## Files

| File | Purpose |
|------|---------|
| `SKILL.md` | Agent instructions and workflow |
| `templates/setup.sql` | Create DB, sample data, semantic view, search service |
| `templates/create-agent.sql` | CREATE AGENT with full specification |
| `templates/invoke-agent.sql` | Call agent via REST API and SQL |
