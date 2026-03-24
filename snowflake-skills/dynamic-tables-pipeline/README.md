# Dynamic Tables Pipeline

Teaches AI coding agents to build declarative data pipelines using Snowflake Dynamic Tables with the medallion (bronze/silver/gold) architecture.

## What It Does

This skill guides an AI agent through building a complete data pipeline where each layer is defined as a SQL SELECT statement. Snowflake handles scheduling, dependency resolution, and incremental processing automatically -- no Tasks, Streams, or orchestration code needed.

The demo pipeline transforms raw e-commerce data (customers, orders, items) through bronze (clean/validate), silver (join/enrich), and gold (aggregate) layers.

## Prerequisites

- Snowflake account with CREATE DYNAMIC TABLE privilege
- A warehouse (any size)
- Cortex Code, Cursor, Windsurf, Claude Code, or another AI coding agent

## Usage

### With Cortex Code

```json
{
  "remote": [
    {
      "source": "https://github.com/Snowflake-Labs/snowflake-ai-kit",
      "ref": "main",
      "skills": [{ "name": "dynamic-tables-pipeline" }]
    }
  ]
}
```

### With Other Agents

Copy the `SKILL.md` file into your agent's rules directory. See the [main README](../../README.md) for per-agent instructions.

## Key Concepts

- **TARGET_LAG** -- How fresh the data should be (e.g., `'10 minutes'`). Use `DOWNSTREAM` for intermediate layers.
- **REFRESH_MODE** -- `AUTO` (recommended), `INCREMENTAL`, or `FULL`.
- **Medallion Architecture** -- Bronze (clean), Silver (enrich), Gold (aggregate).
- **IMMUTABLE WHERE** -- Lock historical rows to skip recomputation.

## Learn More

- [Dynamic Tables Documentation](https://docs.snowflake.com/en/user-guide/dynamic-tables-about)
- [CREATE DYNAMIC TABLE](https://docs.snowflake.com/en/sql-reference/sql/create-dynamic-table)
