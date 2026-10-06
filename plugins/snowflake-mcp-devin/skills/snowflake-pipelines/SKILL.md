---
name: snowflake-pipelines
description: >-
  Monitor and manage Snowflake data pipelines — Dynamic Tables, streams,
  tasks, dbt projects, and Snowpipe. Check refresh status, diagnose
  failures, and inspect pipeline dependencies.
---

# Snowflake Pipelines

Monitor and manage data pipelines in Snowflake.

## When to use

- User asks about pipeline status, refresh failures, or data freshness
- User wants to check dynamic table health or target lag
- User asks about streams, tasks, dbt models, or Snowpipe
- User says "why is my data stale" or "what's failing"

## Dynamic Tables

Dynamic Tables are Snowflake's declarative pipeline primitive — SQL defines the transform, Snowflake manages refresh.

**List dynamic tables:**
```sql
SHOW DYNAMIC TABLES IN ACCOUNT;
```

**Check refresh status and lag:**
```sql
SHOW DYNAMIC TABLES LIKE '%my_table%';
-- Key columns: SCHEDULING_STATE, REFRESH_MODE, TARGET_LAG, DATA_TIMESTAMP
```

**Refresh history (find failures):**
```sql
SELECT name, state, refresh_trigger, refresh_end_time, statistics
FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLE_REFRESH_HISTORY())
WHERE state = 'FAILED'
ORDER BY refresh_end_time DESC
LIMIT 20;
```

**Diagnose UPSTREAM_FAILED:**
A dynamic table fails with UPSTREAM_FAILED when a dependency failed. Check the upstream table's refresh history to find the root cause.

## Streams (change data capture)

```sql
-- List streams
SHOW STREAMS IN SCHEMA my_db.my_schema;

-- Check for pending changes
SELECT SYSTEM$STREAM_HAS_DATA('my_db.my_schema.my_stream');
```

## Tasks (scheduled execution)

```sql
-- List tasks
SHOW TASKS IN SCHEMA my_db.my_schema;

-- Task execution history (last 24 hours)
SELECT name, state, error_message, scheduled_time, completed_time
FROM TABLE(INFORMATION_SCHEMA.TASK_HISTORY(
  SCHEDULED_TIME_RANGE_START => DATEADD(hour, -24, CURRENT_TIMESTAMP())
))
ORDER BY scheduled_time DESC
LIMIT 20;
```

## dbt on Snowflake

```sql
-- List deployed dbt projects (if using snow dbt deploy)
SHOW DBT PROJECTS IN ACCOUNT;

-- Describe a deployed project
DESCRIBE DBT PROJECT my_db.my_schema.my_project;
```

dbt models typically materialize as tables, views, or dynamic tables. Check the target schema for the materialized objects.

## Snowpipe (continuous ingestion)

```sql
-- List pipes
SHOW PIPES IN SCHEMA my_db.my_schema;

-- Check pipe status
SELECT SYSTEM$PIPE_STATUS('my_db.my_schema.my_pipe');

-- Recent copy history
SELECT * FROM TABLE(INFORMATION_SCHEMA.COPY_HISTORY(
  TABLE_NAME => 'my_table',
  START_TIME => DATEADD(hour, -24, CURRENT_TIMESTAMP())
))
ORDER BY LAST_LOAD_TIME DESC
LIMIT 20;
```

## Diagnosis checklist

1. **Data is stale** → Check dynamic table `DATA_TIMESTAMP` or refresh history
2. **Pipeline failed** → Check `DYNAMIC_TABLE_REFRESH_HISTORY()` for state=FAILED
3. **UPSTREAM_FAILED** → Trace upstream dependencies, fix the root failure first
4. **Task not running** → Check if task is suspended (`SHOW TASKS`), check `TASK_HISTORY()`
5. **Snowpipe not loading** → Check `SYSTEM$PIPE_STATUS`, verify stage files and notifications
