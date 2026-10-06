# Snowflake MCP — Always-On Context

You are connected to a Snowflake account through a Managed MCP Server. This gives you governed access to Snowflake's data platform — SQL execution, Cortex AI services, and the full object model.

## Tool discovery

The MCP server exposes one or more tools. Common configurations:

| Tool name pattern | MCP type | What it does |
|---|---|---|
| `cortex_code_agent` | CORTEX_AGENT_RUN | Full Cortex Coding Agent — SQL, file ops, bash, skills |
| `sql_exec` | SYSTEM_EXECUTE_SQL | Direct SQL execution (often read-only) |
| `cortex_analyst` | CORTEX_ANALYST_MESSAGE | Natural language to SQL via semantic views |
| `cortex_search` | CORTEX_SEARCH_SERVICE_QUERY | Semantic search over unstructured data |

Tool names are set by the admin. Use the MCP tool list to discover what's available and adapt your approach.

## Cortex Agent patterns

When the tool is `CORTEX_AGENT_RUN`, send a `text` message. The agent orchestrates internally (SQL, Cortex Analyst, Search, code execution) and returns results. Use `thread_id` from a previous response to continue a multi-turn conversation.

## When to use Cortex Analyst vs raw SQL

- **Cortex Analyst** (if available): Prefer for data questions — "what was Q3 revenue?", "top customers by spend". It queries through governed semantic views with verified queries. Results are auditable.
- **Raw SQL**: Use for admin tasks (SHOW, DESCRIBE, GRANT), DDL, DML, and data questions where no semantic view covers the domain.

## Cortex Search

When available, use for unstructured/semantic search. Pass `query` (required), optional `columns`, `filter`, and `limit`. Results are relevance-ranked. Good for: support tickets, documents, knowledge bases.

## Semantic views

Semantic views are the governed data model layer. They define entities, dimensions, metrics, time grains, and relationships over physical tables. Cortex Analyst queries through them.

- `SHOW SEMANTIC VIEWS` / `DESCRIBE SEMANTIC VIEW <name>` to inspect
- Dimensions = group-by columns, metrics = aggregations, time dimensions = date/timestamp columns
- Verified queries (VQRs) are pre-validated SQL patterns the analyst can reference
- If a user asks about metrics that map to a semantic view, route through Cortex Analyst

## Dynamic Tables and pipelines

Dynamic Tables are Snowflake's declarative pipeline primitive — SQL defines the transform, Snowflake manages the refresh.

- `SHOW DYNAMIC TABLES` — list all, check `SCHEDULING_STATE` and `REFRESH_MODE`
- `DESCRIBE DYNAMIC TABLE <name>` — see the defining SQL and upstream dependencies
- `TARGET_LAG` controls freshness (e.g., `1 hour`, `downstream`)
- Check refresh history: `SELECT * FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLE_REFRESH_HISTORY()) ORDER BY REFRESH_END_TIME DESC LIMIT 20`
- Common failure: `UPSTREAM_FAILED` — a dependency failed, fix that first

Also relevant:
- **Streams**: `SHOW STREAMS` — CDC tracking on tables. `SYSTEM$STREAM_HAS_DATA('<stream>')` checks for pending changes.
- **Tasks**: `SHOW TASKS` — scheduled/triggered execution. Check `TASK_HISTORY()` for failures.
- **Snowpipe**: `SHOW PIPES`, `SYSTEM$PIPE_STATUS('<pipe>')` for ingestion status.

## dbt on Snowflake

When querying dbt-managed objects:
- dbt models materialize as tables, views, or dynamic tables
- `SHOW DBT PROJECTS` lists deployed dbt projects (if using `snow dbt deploy`)
- `DESCRIBE DBT PROJECT <name>` shows project details and versions
- Respect the naming convention — dbt models are typically `schema.model_name`

## DCM (Database Change Management) projects

DCM is infrastructure-as-code for Snowflake — manifest.yml with DEFINE blocks for databases, schemas, tables, roles.

- `SHOW DBT PROJECTS` — DCM projects also appear here
- Three-tier role pattern: `<project>_ADMIN`, `<project>_READWRITE`, `<project>_READONLY`
- CLI: `snow dcm deploy`, `snow dcm execute`, `snow dcm list`
- SQL: `EXECUTE DBT PROJECT`, `ALTER DBT PROJECT`

## Governance

Snowflake enforces governance at the platform level. Never try to bypass it.

- **Masking policies**: `SHOW MASKING POLICIES`, `SELECT * FROM TABLE(INFORMATION_SCHEMA.POLICY_REFERENCES(...))`. If data appears masked (e.g., `***`), explain to the user that a masking policy is applied.
- **Row access policies**: Filter rows based on the querying role. Results may differ by user.
- **Tags**: `SHOW TAGS`, `TAG_REFERENCES()`. Used for classification (PII, CONFIDENTIAL, etc.).
- **Access history**: `SNOWFLAKE.ACCOUNT_USAGE.ACCESS_HISTORY` — who accessed what.
- **Role hierarchy**: `SHOW GRANTS TO ROLE <role>`, `SHOW GRANTS OF ROLE <role>`.

## Snowflake SQL dialect — key differences

- Identifiers are **case-insensitive** unless double-quoted. `MY_TABLE` = `my_table`.
- Use `ILIKE` for case-insensitive pattern matching (not `LIKE`).
- Use `TRY_CAST(x AS type)` for safe type conversion (returns NULL on failure).
- Semi-structured data: `VARIANT` type, access with `:field` or `['field']`. Use `FLATTEN()` + `LATERAL` to unnest arrays.
- Use `QUALIFY` to filter on window functions without a subquery: `QUALIFY ROW_NUMBER() OVER (...) = 1`.
- `LIMIT` is required on exploratory queries — never return unbounded results.

## Error handling

- **Insufficient privileges**: Report the exact error and tell the user which role/privilege is missing. The MCP server runs under a specific role — you cannot escalate.
- **Query timeout**: Suggest narrowing the query scope, adding filters, or using a larger warehouse.
- **Response truncation**: MCP responses are truncated at 250KB. Use `LIMIT`, aggregation, or narrower `SELECT` to stay under the limit.
- **Object not found**: Check database/schema context. Suggest `SHOW TABLES LIKE '%name%'` to locate.

## Safety rules

1. Default to **read-only** queries (SELECT, SHOW, DESCRIBE). Never run DDL or DML unless the user explicitly asks.
2. Always use `LIMIT` on exploratory queries.
3. Never expose credentials, connection strings, or PATs in responses.
4. If a query could be expensive (full table scan, cross join, large warehouse), warn the user first.
5. Writes run without a confirmation step on the Snowflake side. Before any DDL, DML, or GRANT, state what it will change and get the user's explicit go-ahead in the conversation.
