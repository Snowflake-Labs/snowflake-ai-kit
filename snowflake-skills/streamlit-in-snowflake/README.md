# Streamlit in Snowflake

Deploy Streamlit apps to Snowflake with warehouse or container runtimes. Your data stays in-platform — no ETL, no external hosting.

## What It Does

This skill helps your AI coding agent:

1. **Choose a runtime** — Warehouse (simple, auto-scaled) or container (custom packages, GPU)
2. **Set up infrastructure** — Stage, warehouse, compute pool, grants
3. **Create app code** — Starter app with Snowflake data access patterns
4. **Deploy** — Via SQL (`CREATE STREAMLIT`) or Snowflake CLI (`snow streamlit deploy`)
5. **Configure access** — RBAC grants so other roles can view the app

## When to Use

- Deploying a Streamlit dashboard or interactive app to Snowflake
- Choosing between warehouse and container runtimes
- Setting up the full deployment pipeline (stage → code → deploy → access)

## Files

| File | Purpose |
|------|---------|
| `SKILL.md` | Agent instructions and workflow |
| `templates/setup.sql` | Stage, warehouse, and infrastructure setup |
| `templates/deploy-warehouse.sql` | Warehouse runtime deployment |
| `templates/deploy-container.sql` | Container runtime deployment |
| `templates/streamlit_app.py` | Starter app with Snowflake data access |

## Prerequisites

- Snowflake account with `CREATE STREAMLIT` privilege
- A warehouse (both runtimes)
- A compute pool (container runtime only)
- Snowflake CLI 3.14+ (optional, for CLI deployment)

## Quick Start

```sql
-- Simplest possible deployment (warehouse runtime, default files)
CREATE STREAMLIT my_app
  QUERY_WAREHOUSE = my_warehouse;

ALTER STREAMLIT my_app ADD LIVE VERSION FROM LAST;
```

## Links

- [Streamlit in Snowflake docs](https://docs.snowflake.com/en/developer-guide/streamlit/about-streamlit)
- [CREATE STREAMLIT reference](https://docs.snowflake.com/en/sql-reference/sql/create-streamlit)
- [Runtime environments](https://docs.snowflake.com/en/developer-guide/streamlit/app-development/runtime-environments)
