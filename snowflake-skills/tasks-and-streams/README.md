# Tasks and Streams

Teaches AI coding agents to build change data capture (CDC) pipelines with Snowflake Streams and Tasks.

## What It Does

This skill guides an AI agent through building CDC pipelines where Streams capture data changes (inserts, updates, deletes) and Tasks process them on a schedule. Includes patterns for MERGE-based incremental processing, SCD Type 2 history tracking, and multi-step task graphs (DAGs).

## Prerequisites

- Snowflake account with EXECUTE TASK privilege
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
      "skills": [{ "name": "tasks-and-streams" }]
    }
  ]
}
```

### With Other Agents

Copy the `SKILL.md` file into your agent's rules directory. See the [main README](../../README.md) for per-agent instructions.

## Key Concepts

- **Stream** -- Watches a table for changes (INSERT, UPDATE, DELETE) and records them as queryable rows.
- **Task** -- Scheduled SQL job that can depend on other tasks and conditionally run when streams have data.
- **METADATA$ACTION** -- Stream column indicating whether a change was an INSERT or DELETE.
- **SYSTEM$STREAM_HAS_DATA** -- Function that checks if a stream has unconsumed changes (used in WHEN clause).

## When to Use Tasks and Streams vs Dynamic Tables

| Use Case | Recommended |
|----------|-------------|
| Declarative SQL pipelines | Dynamic Tables |
| Procedural logic / stored procedures | Tasks and Streams |
| SCD Type 2 history | Tasks and Streams |
| External API calls | Tasks and Streams |
| Simple transformations | Dynamic Tables |

## Learn More

- [Streams Documentation](https://docs.snowflake.com/en/user-guide/streams)
- [Tasks Documentation](https://docs.snowflake.com/en/user-guide/tasks-intro)
- [CREATE STREAM](https://docs.snowflake.com/en/sql-reference/sql/create-stream)
- [CREATE TASK](https://docs.snowflake.com/en/sql-reference/sql/create-task)
