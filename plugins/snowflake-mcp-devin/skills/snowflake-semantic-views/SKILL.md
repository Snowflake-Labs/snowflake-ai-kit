---
name: snowflake-semantic-views
description: >-
  Create, inspect, and manage semantic views in Snowflake. Semantic views
  define the governed data model (entities, dimensions, metrics, relationships)
  that Cortex Analyst queries through.
---

# Snowflake Semantic Views

Semantic views are the governed data model layer in Snowflake. They define entities, dimensions, metrics, time dimensions, and relationships over physical tables. Cortex Analyst generates SQL through these models.

## When to use

- User asks "what semantic views exist", "show me the data model"
- User wants to create or modify a semantic view
- User asks about available metrics, dimensions, or relationships
- User wants to validate a semantic model or add verified queries

## Discovery

**List semantic views:**
```sql
SHOW SEMANTIC VIEWS IN ACCOUNT;
-- or scoped:
SHOW SEMANTIC VIEWS IN SCHEMA my_db.my_schema;
```

**Describe a semantic view:**
```sql
DESCRIBE SEMANTIC VIEW my_db.my_schema.revenue_model;
```

## Creating a semantic view

Semantic views are defined in YAML and created with SQL:

```sql
CREATE OR REPLACE SEMANTIC VIEW my_db.my_schema.revenue_model AS $$
name: Revenue Model
tables:
  - name: ORDERS
    base_table:
      database: MY_DB
      schema: MY_SCHEMA
      table: ORDERS
    dimensions:
      - name: ORDER_ID
        expr: ORDER_ID
        data_type: NUMBER
      - name: CUSTOMER_NAME
        expr: CUSTOMER_NAME
        data_type: VARCHAR
      - name: REGION
        expr: REGION
        data_type: VARCHAR
    time_dimensions:
      - name: ORDER_DATE
        expr: ORDER_DATE
        data_type: DATE
    metrics:
      - name: TOTAL_REVENUE
        expr: SUM(AMOUNT)
        data_type: NUMBER
        description: Total revenue from orders
      - name: ORDER_COUNT
        expr: COUNT(*)
        data_type: NUMBER
        description: Number of orders
$$;
```

## Key concepts

- **Entities**: Logical tables in the model, mapped to physical base tables
- **Dimensions**: Columns you group by or filter on (categorical, text, numeric IDs)
- **Time dimensions**: Date/timestamp columns for time-series analysis
- **Metrics**: Aggregation expressions (SUM, COUNT, AVG, etc.)
- **Relationships**: Joins between entities (defined with join keys and relationship type)
- **Verified queries (VQRs)**: Pre-validated question-to-SQL pairs that improve Analyst accuracy

## Verified queries

VQRs teach Cortex Analyst the correct SQL for specific questions:

```yaml
verified_queries:
  - name: monthly_revenue
    question: "What is the monthly revenue?"
    verified_query: >-
      SELECT DATE_TRUNC('month', ORDER_DATE) AS month,
             SUM(AMOUNT) AS revenue
      FROM MY_DB.MY_SCHEMA.ORDERS
      GROUP BY month
      ORDER BY month
```

## Relationships (joins)

```yaml
relationships:
  - name: orders_to_customers
    left_table: ORDERS
    right_table: CUSTOMERS
    join_type: many_to_one
    relationship_columns:
      - left_column: CUSTOMER_ID
        right_column: ID
```

## Validation

After creating a semantic view:
1. `DESCRIBE SEMANTIC VIEW <name>` — verify it parsed correctly
2. Test through Cortex Analyst — ask a question that should hit the model
3. Compare the generated SQL against expected patterns
4. Add verified queries for important business questions

## Tips

- Keep entity names matching the physical table names for clarity
- Write clear `description` fields on metrics — Analyst uses them to pick the right metric
- Time dimensions should cover the primary date column for each fact table
- Start with 3-5 verified queries for the most common questions
