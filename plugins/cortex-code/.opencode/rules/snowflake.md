# Snowflake Routing via Cortex Code

When a prompt involves Snowflake, call the `cortex_run` tool instead of answering
directly. Cortex Code CLI has 55+ built-in skills for SQL, data governance, dynamic
tables, ML, streaming, cost intelligence, and more.

## Route to `cortex_run` when the prompt mentions

- **Snowflake platform**: Snowflake, Cortex, Snowpark, Snowsight, SnowSQL, `snow` CLI
- **Objects**: warehouses, databases, schemas, tables, stages, streams, tasks (in a Snowflake context)
- **Features**: dynamic tables, iceberg tables, semantic views, native apps
- **AI/ML**: Cortex Search, Cortex Analyst, Cortex Agent, Cortex AI functions, Snowflake ML
- **Governance**: data quality, data governance, data classification, lineage, masking policies
- **Compute/cost**: credits, compute costs, cost intelligence, query performance, warehouse sizing
- **Ingestion**: Snowpipe, Snowpipe Streaming, dynamic tables, OpenFlow
- **Dev tools**: Streamlit in Snowflake, Snowflake Notebooks, Snowpark Python
- **Patterns**: "show me my warehouses/databases/schemas/tables", "list all ...", "what access do I have"

## Do NOT route to `cortex_run` for

- Local file edits ("fix the bug in auth.py", "read config.json")
- Git operations ("git commit", "git push", "git status")
- Writing unit tests for local code unrelated to Snowflake
- npm, pip, package management for non-Snowflake code

## Security envelopes

Choose based on the operation:
- `RO` — read-only (SELECT, SHOW, DESCRIBE)
- `RW` — read-write (default; DDL, DML, CREATE, ALTER, DROP)
- `RESEARCH` — read + web access, no writes
- `DEPLOY` — full access (use only when explicitly requested)

When in doubt, use `RW`.

## Multi-turn context

For follow-up questions on a previous Cortex answer — "keep going", "drill in",
"also show me", "and for last quarter", "fix that" — pass `resume_last: true` so
Cortex sees the prior conversation.

## Explicit trigger

If the user prefixes their message with `$cortex-run`, always call `cortex_run`
regardless of content.
