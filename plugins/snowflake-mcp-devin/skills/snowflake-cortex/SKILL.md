---
name: snowflake-cortex
description: >-
  Use Cortex AI services — Cortex Analyst for natural-language-to-SQL
  through semantic views, Cortex Search for semantic search, and Cortex
  Agents for orchestrated AI tasks.
---

# Snowflake Cortex AI

Use Snowflake's Cortex AI services when they are available on the MCP server.

## When to use

- User asks a data question and semantic views are configured (Cortex Analyst)
- User wants to search unstructured data like support tickets or documents (Cortex Search)
- User wants to interact with a Cortex Agent for multi-step tasks

## Discover available Cortex services

```sql
-- Semantic views (data models for Cortex Analyst)
SHOW SEMANTIC VIEWS IN ACCOUNT;

-- Cortex Search services
SHOW CORTEX SEARCH SERVICES IN ACCOUNT;

-- Cortex Agents
SHOW AGENTS IN ACCOUNT;
```

## Cortex Analyst

Cortex Analyst converts natural language questions into SQL using semantic views. If the MCP server exposes a `CORTEX_ANALYST_MESSAGE` tool, pass the user's question as the `message`.

**When to prefer Analyst over raw SQL:**
- The question maps to metrics/dimensions defined in a semantic view
- The user is asking business questions ("what was revenue last quarter?")
- Governance and auditability matter

**When to use raw SQL instead:**
- Admin tasks (SHOW, DESCRIBE, GRANT)
- DDL/DML operations
- No semantic view covers the domain

## Cortex Search

Cortex Search provides semantic search over unstructured text columns. If the MCP server exposes a `CORTEX_SEARCH_SERVICE_QUERY` tool:

```json
{
  "query": "billing dispute resolution",
  "columns": ["TICKET_ID", "CUSTOMER_NAME", "REQUEST"],
  "limit": 10
}
```

**Filter syntax** (optional):
```json
{
  "query": "network outage",
  "filter": { "@eq": { "SERVICE_TYPE": "Cloud" } },
  "limit": 5
}
```

Supported filter operators: `@eq`, `@contains` (arrays), `@gte`, `@lte`, composed with `@and`, `@or`, `@not`.

## Cortex Agents

If the MCP server wraps a Cortex Agent (`CORTEX_AGENT_RUN`), send a `text` message. The agent decides which internal tools to use (SQL, Analyst, Search, code execution).

For multi-turn conversations, include `thread_id` from the previous response.

## Examples

- "What was total revenue by region last quarter?" → Route to Cortex Analyst
- "Search support tickets about billing errors" → Route to Cortex Search
- "Analyze our customer churn data and create a visualization" → Route to Cortex Agent
