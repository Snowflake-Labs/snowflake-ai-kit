---
name: tasks-and-streams
description: "Build change data capture pipelines with Snowflake Streams and Tasks. Use for: CDC pipelines, incremental processing, task graphs, scheduled SQL, SCD Type 2, stream consumption. Triggers: stream, task, change data capture, CDC, incremental load, task graph, scheduled task, SYSTEM$STREAM_HAS_DATA, MERGE INTO."
---

# Tasks and Streams

Build change data capture (CDC) pipelines using Snowflake Streams and Tasks. Streams watch a source table for changes (inserts, updates, deletes) and Tasks process those changes on a schedule. Together they enable incremental data processing without external orchestration.

## When to Use

- User wants to capture and process data changes incrementally
- User mentions CDC, change data capture, or streams
- User needs scheduled SQL jobs or task automation
- User wants to build task dependency graphs (DAGs)
- User asks about SCD Type 2 history tracking
- User needs MERGE-based incremental processing
- User needs procedural logic, external API calls, or conditional branching that Dynamic Tables cannot handle

**Consider Dynamic Tables first.** For most new pipelines, Dynamic Tables are simpler (no orchestration code). Use Tasks and Streams when you need: procedural logic (stored procedures), external API calls, complex conditional branching, SCD Type 2 history, or fine-grained scheduling control.

## Tools Used

- `snowflake_sql_execute` -- Create databases, schemas, tables, streams, tasks, verify data
- `ask_user_question` -- Confirm targets, get approval at checkpoints
- `read` / `write` / `edit` -- Configure SQL templates with user-specific values

## Bundled Files

```
tasks-and-streams/
├── SKILL.md                    # This file (agent instructions)
├── README.md                   # Human-facing docs
└── templates/
    ├── setup.sql               # Create demo DB, source/target tables, seed data
    ├── cdc-pipeline.sql        # Stream + Task + MERGE (incremental CDC)
    └── task-graph.sql          # Multi-step DAG with AFTER dependencies
```

## Stopping Points

- Phase 0: User approves the workflow before any action
- Step 1: User confirms target objects (database, schema, warehouse, role)
- Step 5: User verifies CDC data before building task graph
- Step 7: User verifies monitoring output

---

## Phase 0: Briefing and Consent

Present the following briefing to the user:

> ### Tasks and Streams -- What This Skill Does
>
> **Streams** are Snowflake's built-in change data capture (CDC). They watch a table and record every INSERT, UPDATE, and DELETE as queryable rows. **Tasks** are scheduled SQL jobs that can run on a cron schedule, depend on other tasks (DAGs), and conditionally execute only when a stream has data.
>
> This skill builds two patterns:
> 1. **CDC pipeline** -- stream watches source table, task applies changes to target via MERGE
> 2. **Task graph (DAG)** -- multi-step pipeline with dependencies (raw -> staged -> aggregated)
>
> **What will happen (7 steps):**
>
> 1. **Gather target details** -- confirm database, schema, warehouse, role
> 2. **Create source and target tables** -- with seed data
> 3. **Create stream** -- CDC on the source table
> 4. **Build CDC task** -- MERGE-based incremental processing
> 5. **Resume and test** -- insert/update/delete, verify target
> 6. **Build task graph** -- optional: multi-step DAG with AFTER dependencies
> 7. **Monitor and verify** -- task history, stream status, row counts
>
> **What this skill will NOT do:**
> - Drop or alter any existing objects not created by this workflow
> - Continue past any checkpoint without your approval

Ask the user: **"Shall I proceed with Step 1 (Gather Target Details)?"**

Do NOT proceed until the user confirms.

---

## Workflow

### Step 1: Gather Target Details

Propose defaults and let the user override:

| Object | Default | Notes |
|--------|---------|-------|
| **Database** | `STREAMS_TASKS_DEMO` | Created if it does not exist |
| **Schema** | `CDC` | Created if it does not exist |
| **Warehouse** | `COMPUTE_WH` | Any X-Small is fine |
| **Role** | `ACCOUNTADMIN` | Must have EXECUTE TASK privilege |

Confirm with the user before proceeding.

---

### Step 2: Create Source and Target Tables

Run `templates/setup.sql` after replacing `{{DATABASE}}`, `{{SCHEMA}}`, `{{ROLE}}` with confirmed values.

This creates:
- `SOURCE_ORDERS` (500 rows) -- simulates external system or landing zone
- `DWH_ORDERS` -- target warehouse table (starts empty)
- `DWH_ORDERS_HISTORY` -- SCD Type 2 history table (starts empty)

---

### Step 3: Create Stream

Explain stream types to the user:

| Type | Tracks | Use Case |
|------|--------|----------|
| **Standard** (default) | INSERT, UPDATE, DELETE | General CDC, MERGE pipelines |
| **Append-only** | INSERT only | Staging tables, event logs |

Stream metadata columns:
- `METADATA$ACTION` -- `'INSERT'` or `'DELETE'`
- `METADATA$ISUPDATE` -- `TRUE` if the row is part of an UPDATE (appears as DELETE + INSERT pair)
- `METADATA$ROW_ID` -- unique ID for the changed row

**Critical rule:** Streams are consumed by DML statements (INSERT, MERGE, etc.) within a committed transaction. A SELECT alone does NOT consume stream data. If the transaction rolls back, stream data is NOT consumed.

---

### Step 4: Build CDC Task

Run `templates/cdc-pipeline.sql` after replacing placeholders.

This creates:
- `SOURCE_ORDERS_STREAM` -- standard stream on the source table
- `PROCESS_ORDER_CHANGES` -- task with `WHEN SYSTEM$STREAM_HAS_DATA()` that runs a MERGE
- `SOURCE_ORDERS_HISTORY_STREAM` + `TRACK_ORDER_HISTORY` -- optional SCD Type 2 tracking

The MERGE handles inserts, updates, and deletes in a single statement, making it idempotent.

---

### Step 5: Resume and Test

Resume tasks:
```sql
ALTER TASK TRACK_ORDER_HISTORY RESUME;
ALTER TASK PROCESS_ORDER_CHANGES RESUME;
```

Test with source changes:
```sql
-- Insert new order
INSERT INTO SOURCE_ORDERS (order_id, customer_id, product_name, amount, order_date)
    VALUES (9001, 42, 'New Product', 99.99, CURRENT_DATE());

-- Update existing order
UPDATE SOURCE_ORDERS SET amount = 149.99, status = 'UPDATED' WHERE order_id = 1;

-- Delete an order
DELETE FROM SOURCE_ORDERS WHERE order_id = 2;
```

Wait ~5 minutes for the task to run, then verify:
```sql
SELECT COUNT(*) FROM DWH_ORDERS;
SELECT * FROM DWH_ORDERS WHERE order_id IN (1, 2, 9001);
SELECT * FROM DWH_ORDERS_HISTORY WHERE order_id = 1 ORDER BY valid_from;
```

Confirm with the user that the CDC pipeline processed correctly.

---

### Step 6: Build Task Graph (Optional)

Ask the user if they want to build a multi-step task graph.

Run `templates/task-graph.sql` after replacing placeholders.

This creates:
- `STAGED_ORDERS` + `ORDER_METRICS` -- supporting tables
- `STAGE_RAW_ORDERS` -- root task (scheduled, reads from stream)
- `AGGREGATE_ORDER_METRICS` -- child task (runs AFTER root, aggregates staged data)

**Resume in reverse dependency order (children first, root last!):**
```sql
ALTER TASK AGGREGATE_ORDER_METRICS RESUME;
ALTER TASK STAGE_RAW_ORDERS RESUME;
```

---

### Step 7: Monitor and Verify

```sql
-- Task run history
SELECT *
FROM TABLE(INFORMATION_SCHEMA.TASK_HISTORY(
    TASK_NAME => 'PROCESS_ORDER_CHANGES',
    SCHEDULED_TIME_RANGE_START => DATEADD('hour', -1, CURRENT_TIMESTAMP())
)) ORDER BY SCHEDULED_TIME DESC;

-- All tasks in schema
SHOW TASKS IN SCHEMA {{DATABASE}}.{{SCHEMA}};

-- Stream status
SHOW STREAMS IN SCHEMA {{DATABASE}}.{{SCHEMA}};

-- Check if stream has unconsumed data
SELECT SYSTEM$STREAM_HAS_DATA('SOURCE_ORDERS_STREAM');
```

---

## Patterns

### Serverless Tasks (No Warehouse)

```sql
CREATE OR REPLACE TASK my_serverless_task
    USER_TASK_MANAGED_INITIAL_WAREHOUSE_SIZE = 'XSMALL'
    SCHEDULE = '5 MINUTE'
    WHEN SYSTEM$STREAM_HAS_DATA('my_stream')
AS ...;
```

Snowflake manages compute. No warehouse needed. Billed per-second at serverless rates.

### Cron Schedule

```sql
CREATE OR REPLACE TASK daily_report
    WAREHOUSE = compute_wh
    SCHEDULE = 'USING CRON 0 6 * * * America/Los_Angeles'
AS ...;
```

### Task Graph (DAG)

```sql
-- Root task (scheduled)
CREATE TASK load_raw WAREHOUSE = wh SCHEDULE = '10 MINUTE' AS ...;
-- Child (runs after root)
CREATE TASK transform WAREHOUSE = wh AFTER load_raw AS ...;
-- Grandchild (runs after transform)
CREATE TASK aggregate WAREHOUSE = wh AFTER transform AS ...;

-- Resume children first, root last!
ALTER TASK aggregate RESUME;
ALTER TASK transform RESUME;
ALTER TASK load_raw RESUME;
```

### Append-Only Stream

```sql
CREATE OR REPLACE STREAM staging_stream
    ON TABLE landing_table
    APPEND_ONLY = TRUE;
```

Only tracks INSERTs. More efficient for staging/landing tables where updates and deletes do not occur.

---

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| **Task not running** | Tasks are suspended by default after creation | `ALTER TASK ... RESUME` |
| **Stream shows no data** | Data consumed by previous DML transaction | Insert new changes to source table |
| **Stream is stale** | Unconsumed past DATA_RETENTION_TIME_IN_DAYS (default 14 days) | Recreate stream, increase retention |
| **SYSTEM$STREAM_HAS_DATA returns false** | No new changes since last consumption | Verify source table has new DML |
| **Task graph wrong order** | Root resumed before children | Resume children first, root task last |
| **EXECUTE TASK privilege error** | Role lacks task execution rights | `GRANT EXECUTE TASK ON ACCOUNT TO ROLE <role>` |
| **Duplicate processing** | Non-idempotent INSERT from stream | Use MERGE (idempotent) instead of INSERT |
| **Task skipped execution** | WHEN condition evaluated to false | Normal -- no warehouse cost incurred. Check stream has data. |

---

## Architecture Notes

- **Streams** = CDC built into Snowflake. They track INSERT, UPDATE, DELETE on a source table and present changes as queryable rows.
- **Tasks** = scheduled SQL jobs. They can depend on other tasks (DAG), conditionally run when streams have data, and use warehouse or serverless compute.
- **Standard streams** track all DML. **Append-only streams** only track INSERTs (more efficient for staging tables).
- The `WHEN` clause is evaluated every schedule interval. If false, no warehouse is spun up (no cost).
- Stream data is consumed by DML in a committed transaction. SELECT does not consume. Rollback does not consume.
- A stream can only be consumed by one DML at a time within a single transaction.
- Stale streams (unconsumed past retention period, default 14 days) become unusable and must be recreated.
- Task graphs support up to 1000 tasks. Resume order: children first, root last.
- For most new pipelines, **Dynamic Tables are recommended** over Tasks and Streams. They handle orchestration automatically. Use Tasks and Streams when you need: procedural logic, external API calls, SCD Type 2, complex branching, or stored procedure calls.

## Output

- Demo database with source table, target table, and history table
- CDC pipeline: stream + task + MERGE for incremental processing
- Optional: task graph (DAG) with multi-step dependencies
- Monitoring queries for task history and stream status
