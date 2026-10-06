---
name: snowflake-explore
description: >-
  Discover databases, schemas, tables, views, and columns in Snowflake.
  Use when the user wants to understand what data is available or inspect
  table structure.
---

# Snowflake Explore

Discover and understand the data landscape in a Snowflake account.

## When to use

- User asks "what data is available", "show me the tables", "what databases exist"
- User wants to inspect a table's columns, types, or sample data
- User needs to find a table by name or pattern

## Discovery patterns

**List databases:**
```sql
SHOW DATABASES;
```

**List schemas in a database:**
```sql
SHOW SCHEMAS IN DATABASE my_db;
```

**List tables in a schema:**
```sql
SHOW TABLES IN SCHEMA my_db.my_schema;
```

**Find tables by name pattern:**
```sql
SHOW TABLES LIKE '%order%' IN ACCOUNT;
```

**Describe a table (columns and types):**
```sql
DESCRIBE TABLE my_db.my_schema.orders;
```

**Full column metadata:**
```sql
SELECT column_name, data_type, is_nullable, column_default
FROM my_db.INFORMATION_SCHEMA.COLUMNS
WHERE table_schema = 'MY_SCHEMA' AND table_name = 'ORDERS'
ORDER BY ordinal_position;
```

**Preview data (always use LIMIT):**
```sql
SELECT * FROM my_db.my_schema.orders LIMIT 5;
```

**Find views:**
```sql
SHOW VIEWS IN SCHEMA my_db.my_schema;
```

**Find dynamic tables:**
```sql
SHOW DYNAMIC TABLES IN SCHEMA my_db.my_schema;
```

**Find stages (file storage):**
```sql
SHOW STAGES IN SCHEMA my_db.my_schema;
```

**Find streams (change tracking):**
```sql
SHOW STREAMS IN SCHEMA my_db.my_schema;
```

## Tips

- SHOW commands accept LIKE patterns: `SHOW TABLES LIKE '%customer%'`
- Use IN ACCOUNT to search across all databases (requires privileges)
- Snowflake identifiers are case-insensitive unless double-quoted
- INFORMATION_SCHEMA requires uppercase for filter values
