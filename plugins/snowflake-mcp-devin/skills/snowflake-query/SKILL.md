---
name: snowflake-query
description: >-
  Run SQL queries against Snowflake through the Managed MCP Server.
  Use for data retrieval, aggregations, joins, semi-structured data,
  time travel, and any explicit SQL the user requests.
---

# Snowflake Query

Run SQL queries against Snowflake. Use this skill when the user asks to query data, run SQL, or retrieve specific results.

## When to use

- User asks to query, select, or look at data
- User provides a specific SQL statement to run
- User asks about row counts, aggregations, or filtered results
- User needs joins, window functions, or CTEs

## How to use

1. Identify the SQL. Use Snowflake dialect (ILIKE, TRY_CAST, FLATTEN, QUALIFY).
2. Call the MCP server's SQL execution tool (or Cortex Agent) with the query.
3. Summarize results. For large sets, show a sample and total count.

## Examples

**Simple count:**
```sql
SELECT COUNT(*) AS row_count FROM my_db.my_schema.orders;
```

**Top-N with aggregation:**
```sql
SELECT customer_name, SUM(amount) AS total_revenue
FROM orders
GROUP BY customer_name
ORDER BY total_revenue DESC
LIMIT 10;
```

**Join with filter:**
```sql
SELECT o.order_id, c.name, o.amount
FROM orders o
JOIN customers c ON o.customer_id = c.id
WHERE o.created_at >= DATEADD(day, -30, CURRENT_DATE())
ORDER BY o.amount DESC
LIMIT 20;
```

**Semi-structured (VARIANT/JSON):**
```sql
SELECT
  raw:event_type::STRING AS event_type,
  raw:user.name::STRING AS user_name,
  raw:timestamp::TIMESTAMP AS event_time
FROM events
WHERE raw:event_type::STRING ILIKE '%purchase%'
LIMIT 10;
```

**Flatten arrays:**
```sql
SELECT t.order_id, f.value:product_name::STRING AS product
FROM orders t,
LATERAL FLATTEN(input => t.items) f
LIMIT 20;
```

**Time travel:**
```sql
SELECT * FROM orders AT(TIMESTAMP => '2025-01-15 10:00:00'::TIMESTAMP) LIMIT 10;
```

**Window function with QUALIFY:**
```sql
SELECT customer_id, order_date, amount
FROM orders
QUALIFY ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date DESC) = 1;
```

## Important

- Default to read-only (SELECT). Never run DDL/DML unless explicitly requested.
- Always use LIMIT on exploratory queries.
- If a query fails, report the error and suggest a fix.
- MCP responses truncate at 250KB — aggregate or narrow your SELECT if results are large.
