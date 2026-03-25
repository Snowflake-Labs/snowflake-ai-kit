---
name: dynamic-tables-pipeline
description: "Build declarative data pipelines with Snowflake Dynamic Tables using the medallion architecture (bronze/silver/gold). Use for: creating dynamic tables, setting target lag, incremental refresh, monitoring pipelines, migrating from tasks and streams. Triggers: dynamic table, data pipeline, medallion architecture, bronze silver gold, target lag, incremental refresh, declarative pipeline."
---

# Dynamic Tables Pipeline

Build a declarative data pipeline using Snowflake Dynamic Tables. Instead of writing orchestration code with Tasks and Streams, you define each transformation as a SELECT statement and Snowflake handles the refresh scheduling, dependency ordering, and incremental processing automatically.

## When to Use

- User wants to build a data pipeline on Snowflake without manual orchestration
- User mentions dynamic tables, target lag, or declarative pipelines
- User asks about medallion architecture (bronze/silver/gold) on Snowflake
- User wants to migrate from Tasks and Streams to a simpler approach
- User needs incremental refresh or near-real-time data transformations

## Tools Used

- `snowflake_sql_execute` -- Create databases, schemas, raw tables, dynamic tables, verify data
- `ask_user_question` -- Confirm targets, get approval at checkpoints
- `read` / `write` / `edit` -- Configure SQL templates with user-specific values

## Bundled Files

```
dynamic-tables-pipeline/
├── SKILL.md                    # This file (agent instructions)
├── README.md                   # Human-facing docs
└── templates/
    ├── setup.sql               # Create demo DB, raw tables, seed data
    ├── bronze.sql              # Bronze DTs (clean/validate)
    ├── silver.sql              # Silver DT (join/enrich)
    └── gold.sql                # Gold DTs (aggregate metrics)
```

## Stopping Points

- Phase 0: User approves the workflow before any action
- Step 1: User confirms target objects (database, schema, warehouse, role)
- Step 3: User verifies bronze layer created and refreshed
- Step 5: User verifies gold layer data before monitoring

---

## Phase 0: Briefing and Consent

Present the following briefing to the user:

> ### Dynamic Tables Pipeline -- What This Skill Does
>
> **Dynamic Tables** are Snowflake's declarative approach to data pipelines. You write a SELECT statement, set a freshness target (TARGET_LAG), and Snowflake handles the rest -- scheduling, dependency resolution, and incremental processing.
>
> This skill builds a **medallion architecture** (bronze/silver/gold) using sample e-commerce data.
>
> **What will happen (6 steps):**
>
> 1. **Gather target details** -- confirm database, schema, warehouse, role
> 2. **Create demo objects** -- raw tables with seed data (customers, orders, items)
> 3. **Build bronze layer** -- clean and validate raw data
> 4. **Build silver layer** -- join and enrich across tables
> 5. **Build gold layer** -- aggregate business metrics (daily revenue, customer segments)
> 6. **Monitor and verify** -- check refresh history, verify row counts
>
> **What this skill will NOT do:**
> - Drop or alter any existing objects not created by this workflow
> - Modify files outside the project directory
> - Continue past any checkpoint without your approval

Ask the user: **"Shall I proceed with Step 1 (Gather Target Details)?"**

Do NOT proceed until the user confirms.

---

## Workflow

### Step 1: Gather Target Details

Propose defaults and let the user override:

| Object | Default | Notes |
|--------|---------|-------|
| **Database** | `DYNAMIC_TABLES_DEMO` | Created if it does not exist |
| **Schema** | `PIPELINE` | Created if it does not exist |
| **Warehouse** | `COMPUTE_WH` | Any X-Small is fine |
| **Role** | `ACCOUNTADMIN` | Must have CREATE DYNAMIC TABLE privilege |

Confirm with the user before proceeding.

---

### Step 2: Create Demo Objects

Run `templates/setup.sql` after replacing `{{DATABASE}}`, `{{SCHEMA}}` with confirmed values.

This creates:
- `RAW_CUSTOMERS` (100 rows) -- customer profiles with regions
- `RAW_ORDERS` (1000 rows) -- orders with status and amounts
- `RAW_ORDER_ITEMS` (3000 rows) -- line items with products and categories

---

### Step 3: Build Bronze Layer

Run `templates/bronze.sql` after replacing placeholders.

Creates 3 dynamic tables:
- `BRONZE_ORDERS` -- validated orders (nulls removed, status normalized)
- `BRONZE_CUSTOMERS` -- cleaned customers (names capitalized, emails lowered)
- `BRONZE_ORDER_ITEMS` -- validated items with calculated `line_total`

All use `TARGET_LAG = 'DOWNSTREAM'` so the gold layer controls refresh timing.

Verify:
```sql
SHOW DYNAMIC TABLES IN SCHEMA {{DATABASE}}.{{SCHEMA}};
SELECT COUNT(*) FROM BRONZE_ORDERS;
```

Confirm with the user that bronze tables populated correctly.

---

### Step 4: Build Silver Layer

Run `templates/silver.sql` after replacing placeholders.

Creates `SILVER_ORDER_DETAILS` -- joins orders + customers + items with enrichment:
- Customer name and region
- Item count and subtotal per order
- Order tier classification (HIGH/MEDIUM/LOW)

Also uses `TARGET_LAG = 'DOWNSTREAM'`.

---

### Step 5: Build Gold Layer

Run `templates/gold.sql` after replacing placeholders.

Creates 2 dynamic tables with `TARGET_LAG = '10 minutes'`:
- `GOLD_DAILY_REVENUE` -- revenue metrics by date and region
- `GOLD_CUSTOMER_SEGMENTS` -- customer segmentation (VIP/LOYAL/REPEAT/AT_RISK/NEW)

These are the "leaf" tables that drive the entire pipeline's refresh schedule.

Verify:
```sql
SELECT * FROM GOLD_DAILY_REVENUE ORDER BY revenue_date DESC LIMIT 10;
SELECT customer_segment, COUNT(*) FROM GOLD_CUSTOMER_SEGMENTS GROUP BY 1;
```

---

### Step 6: Monitor and Verify

Check refresh status:
```sql
-- Refresh history for a specific DT
SELECT * FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLE_REFRESH_HISTORY(
    NAME => '{{DATABASE}}.{{SCHEMA}}.GOLD_DAILY_REVENUE'
)) ORDER BY REFRESH_START_TIME DESC LIMIT 5;

-- All DTs in schema
SHOW DYNAMIC TABLES IN SCHEMA {{DATABASE}}.{{SCHEMA}};

-- Check scheduling state
SELECT name, target_lag, refresh_mode, scheduling_state
FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLE_GRAPH_HISTORY())
WHERE name LIKE '%{{SCHEMA}}%';
```

Confirm data freshness and pipeline health with the user.

---

## Patterns

### TARGET_LAG Choices

```sql
-- Real-time dashboards
TARGET_LAG = '1 minute'

-- Hourly reports
TARGET_LAG = '30 minutes'

-- Daily aggregates
TARGET_LAG = '6 hours'

-- Let downstream control (for intermediate layers)
TARGET_LAG = 'DOWNSTREAM'
```

Use `DOWNSTREAM` for bronze and silver layers. Set an explicit lag only on gold (leaf) tables.

### REFRESH_MODE Options

- `AUTO` (recommended) -- Snowflake picks incremental or full per-refresh
- `INCREMENTAL` -- Forces incremental. Fails if SQL is not supported incrementally.
- `FULL` -- Forces full recomputation every refresh

### Locking Historical Data

```sql
CREATE DYNAMIC TABLE closed_period_sales
    TARGET_LAG = '30 minutes'
    WAREHOUSE = compute_wh
    IMMUTABLE WHERE (sale_date < '2025-01-01')
    AS SELECT ... FROM transactions GROUP BY 1, 2;
```

Rows matching the IMMUTABLE WHERE predicate are frozen and skip recomputation.

### Schema Changes via Backfill

Dynamic table columns cannot be altered directly. Workaround:

```sql
-- 1. Clone to regular table
CREATE TABLE dt_clone CLONE my_dynamic_table;
-- 2. Modify clone
ALTER TABLE dt_clone ADD COLUMN new_col FLOAT;
-- 3. Recreate DT with backfill
CREATE OR REPLACE DYNAMIC TABLE my_dynamic_table
    BACKFILL FROM dt_clone
    TARGET_LAG = '10 minutes'
    WAREHOUSE = compute_wh
    AS SELECT *, some_calculation AS new_col FROM source;
```

---

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| **UPSTREAM_FAILED** | Base table or upstream DT has an error | Fix upstream DT first, then `ALTER DYNAMIC TABLE ... REFRESH` |
| **Full refresh instead of incremental** | Unsupported SQL (lateral joins, some non-deterministic functions) | Check `REFRESH_MODE` in SHOW DYNAMIC TABLES; simplify SQL or accept full refresh |
| **Schema change needed** | Cannot ALTER DT columns directly | Clone, modify clone, recreate DT with `BACKFILL FROM` |
| **Data staleness** | TARGET_LAG too high or refresh suspended | Check `scheduling_state` in SHOW DYNAMIC TABLES; reduce lag or resume |
| **High credit usage** | TARGET_LAG too aggressive for data volume | Increase lag, use `DOWNSTREAM` for intermediate layers, right-size warehouse |
| **DT suspended** | Manual suspension or error threshold exceeded | `ALTER DYNAMIC TABLE ... RESUME` |

---

## Architecture Notes

- Dynamic Tables replace Tasks and Streams for most pipeline use cases. Use Tasks and Streams when you need procedural logic, external API calls, complex conditional branching, or SCD Type 2.
- Snowflake automatically determines refresh order from the SQL dependency graph. You do not manage scheduling.
- Only "leaf" DTs (those not referenced by other DTs) need an explicit `TARGET_LAG`. Use `DOWNSTREAM` for all intermediate layers.
- `REFRESH_MODE = AUTO` lets Snowflake choose incremental vs full per-refresh based on the SQL and data volume.
- Incremental mode works with most SQL. Exceptions include some lateral joins, non-deterministic functions, and UNION (without ALL).
- DTs support clustering (`CLUSTER BY`), masking policies, row access policies, and tagging -- same as regular tables.
- Maximum chain depth is not limited, but keep pipelines under 10 layers for debuggability.

## Output

- Demo database with bronze/silver/gold dynamic tables
- Automated pipeline that refreshes within 10 minutes of source changes
- Monitoring queries for refresh history and pipeline health
