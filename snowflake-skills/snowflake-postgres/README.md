# Snowflake Postgres

Teach your AI coding agent to create and manage fully managed Postgres instances on Snowflake.

## What It Does

This skill guides an AI coding agent through:
- Creating Postgres instances with proper compute, storage, and networking
- Setting up network policies for Postgres ingress
- Connecting with psql or GUI clients (pgAdmin, DBeaver, DataGrip)
- Loading sample ecommerce data for testing
- Managing instance lifecycle (suspend, resume, drop, reset credentials)

## Prerequisites

- Snowflake account (ACCOUNTADMIN or CREATE POSTGRES INSTANCE privilege)
- Account in a [supported region](https://docs.snowflake.com/en/user-guide/snowflake-postgres/about#regional-availability) (AWS or Azure)
- Local Postgres client for connecting (e.g., `psql`, pgAdmin, DBeaver)

## Usage

### With Cortex Code

```json
{
  "remote": [
    {
      "source": "https://github.com/Snowflake-Labs/snowflake-ai-kit",
      "ref": "main",
      "skills": [{ "name": "snowflake-postgres" }]
    }
  ]
}
```

### With Other Agents

Copy the `SKILL.md` file into your agent's rules directory. See the [main README](../../README.md) for per-agent instructions.

## Resources

- [Snowflake Postgres overview](https://docs.snowflake.com/en/user-guide/snowflake-postgres/about)
- [Getting started guide](https://www.snowflake.com/en/developers/guides/getting-started-with-snowflake-postgres/)
- [CREATE POSTGRES INSTANCE](https://docs.snowflake.com/en/sql-reference/sql/create-postgres-instance)
- [Network policies for Postgres](https://docs.snowflake.com/en/user-guide/snowflake-postgres/network-policies)
