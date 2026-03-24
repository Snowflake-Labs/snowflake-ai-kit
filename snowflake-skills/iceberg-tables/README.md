# Iceberg Tables

Teaches AI coding agents to create and manage Apache Iceberg tables on Snowflake with Snowflake-managed or external catalogs.

## What It Does

This skill guides an AI agent through creating Iceberg tables on Snowflake -- from setting up external volumes and catalog integrations to creating tables, loading data, and configuring cross-engine access. Supports three catalog modes: Snowflake-managed, REST catalog (Polaris/Open Catalog), and files in object storage.

## Prerequisites

- Snowflake account
- Cloud storage bucket (S3, GCS, or Azure Blob) with appropriate IAM permissions
- For external catalogs: a running REST catalog endpoint (Polaris, Open Catalog, etc.)
- Cortex Code, Cursor, Windsurf, Claude Code, or another AI coding agent

## Usage

### With Cortex Code

```json
{
  "remote": [
    {
      "source": "https://github.com/Snowflake-Labs/snowflake-ai-kit",
      "ref": "main",
      "skills": [{ "name": "iceberg-tables" }]
    }
  ]
}
```

### With Other Agents

Copy the `SKILL.md` file into your agent's rules directory. See the [main README](../../README.md) for per-agent instructions.

## Key Concepts

- **External Volume** -- Cloud storage location where Iceberg data and metadata files live.
- **Catalog Integration** -- Connection to an external catalog (REST, Glue, etc.) that manages Iceberg metadata.
- **Snowflake-managed** -- Snowflake acts as the Iceberg catalog. Simplest option with full DML support.
- **CATALOG_SYNC** -- Publishes Snowflake-managed table metadata to an external catalog for cross-engine reads.

## Learn More

- [Iceberg Tables Documentation](https://docs.snowflake.com/en/user-guide/tables-iceberg)
- [CREATE ICEBERG TABLE](https://docs.snowflake.com/en/sql-reference/sql/create-iceberg-table)
- [Configure an External Volume](https://docs.snowflake.com/en/user-guide/tables-iceberg-configure-external-volume)
